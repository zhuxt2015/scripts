# -*- coding: utf-8 -*-
import json
import pymysql
import sys

# 数据库连接配置
db_config = {
    "host": "10.150.4.27",
    "user": "dsuser",
    "password": "Ds@12345",
    "database": "etl_db"
}

starrocks_config = {
    "host": "10.150.3.30",
    "port": 9030,
    "user": "ds",
    "password": "dsSR123!",
    "database": "ds"
}

# 连接到数据库
connection = pymysql.connect(**db_config)

# 指定要查找的工作流名称
workflow_name = "cache_pc"
dt=sys.argv[1]
start_time="{dt} 00:00:00".format(dt=dt)
end_time="{dt} 07:00:00".format(dt=dt)
dependent="DEPENDENT"
dependent_workflows = []
task_info_list = []
values = []
count = 0

insert_query = """
INSERT INTO dm_deptasks (
    project_name, process_name, task_name, dt, submit_time, start_time, end_time, taken_minute, start_diff_second, dod
) VALUES {}
"""

def get_dependent_task(workflow_name):
    
    # 查询t_ds_task_instance表获取工作流"cache_pc"的任务实例ID列表
    with connection.cursor() as cursor:
        # 查询任务实例ID列表
        sql = "SELECT t.id FROM t_ds_task_instance t \
                   LEFT JOIN t_ds_process_instance pi ON t.process_instance_id = pi.id \
                   LEFT JOIN t_ds_process_definition pd ON pi.process_definition_id = pd.id \
                   WHERE pd.name = '{workflow_name}' and date_format(t.submit_time,'%Y-%m-%d')='{dt}' \
                   and task_type='{dependent}' \
                   ".format(workflow_name=workflow_name,dt=dt,dependent=dependent)
        
        cursor.execute(sql)
        result = cursor.fetchall()
        if result:
            
            # 遍历任务实例ID列表，查找依赖工作流
            for row in result:
                task_instance_id = row[0]
                find_dependent_workflows(task_instance_id)

def get_task_info(ids):
    task_info = {}
    project_id = ids[0]
    process_definition_id = ids[1]
    task_instance_id = ids[2]

    # 查询t_ds_task_instance表获取任务信息
    with connection.cursor() as cursor:
        # 根据任务实例ID查询任务信息
        sql = "select a.*,  time_to_sec(timediff(date_format(a.start_time,'%H:%i:%s'),date_format(b.start_time,'%H:%i:%s'))) as diff_second, (a.taken - b.taken)/b.taken as dod from \
        (SELECT p.name as project_name, pd.name as process_name, t.name as task_name, t.submit_time, t.start_time, t.end_time, \
        round(timestampdiff(second, t.start_time,t.end_time)/60,2) as taken FROM t_ds_task_instance t \
               LEFT JOIN t_ds_process_instance pi ON t.process_instance_id = pi.id \
               LEFT JOIN t_ds_process_definition pd ON pi.process_definition_id = pd.id \
               LEFT JOIN t_ds_project p ON pd.project_id = p.id \
               WHERE p.id={project_id} and pd.id={process_definition_id} and t.id = {task_instance_id}) a \
               left join \
               (SELECT t.name as task_name,t.submit_time,t.start_time,round(timestampdiff(second, t.start_time,t.end_time)/60,2) as taken FROM t_ds_task_instance t \
               LEFT JOIN t_ds_process_instance pi ON t.process_instance_id = pi.id \
               LEFT JOIN t_ds_process_definition pd ON pi.process_definition_id = pd.id \
               LEFT JOIN t_ds_project p ON pd.project_id = p.id \
               WHERE p.id={project_id} and pd.id={process_definition_id}) b \
               on a.task_name=b.task_name \
               and date_format(a.submit_time,'%Y-%m-%d') = date_add(date_format(b.submit_time,'%Y-%m-%d'),interval 1 DAY) \
               ".format(task_instance_id=task_instance_id,project_id=project_id, process_definition_id=process_definition_id)
        
        cursor.execute(sql)
        result = cursor.fetchone()
        if result is not None:
            task_info["project_name"] = result[0]
            task_info["process_name"] = result[1]
            task_info["task_name"] = result[2]
            task_info["submit_time"] = result[3]
            task_info["start_time"] = result[4]
            task_info["end_time"] = result[5]
            task_info["taken"] = result[6]
            task_info["diff_second"] = result[7]
            task_info["dod"] = result[8]
            value = (task_info["project_name"],task_info["process_name"],task_info["task_name"],dt,task_info["submit_time"],
            task_info["start_time"],task_info["end_time"],task_info["taken"],task_info["diff_second"],task_info["dod"])
            values.append(value)
    return task_info
    


def find_dependent_workflows(task_instance_id):
    

    # 查询t_ds_task_instance表获取task_json字段
    with connection.cursor() as cursor:
        # 根据任务实例ID查询任务信息
        sql = "SELECT task_json FROM t_ds_task_instance WHERE id = {task_instance_id} ".format(task_instance_id=task_instance_id)
        cursor.execute(sql)
        result = cursor.fetchone()
        if result is not None:
            task_json = result[0]
            task_data = json.loads(task_json)
            
            # 解析dependence字段，查找依赖工作流
            dependence = task_data.get("dependence")
            if dependence:
                dependence=json.loads(dependence)
                depend_task_list = dependence.get("dependTaskList", [])
                for depend_task in depend_task_list:
                    depend_item_list = depend_task.get("dependItemList", [])
                    for depend_item in depend_item_list:
                        dep_tasks = depend_item.get("depTasks")
                        if dep_tasks == "ALL":
                            project_id = depend_item.get("projectId")
                            definition_id = depend_item.get("definitionId")

                            # 查询依赖工作流的所有任务实例ID列表
                            sql = "SELECT name FROM t_ds_process_definition WHERE id = {definition_id} ".format(definition_id=definition_id)
                            cursor.execute(sql)
                            result = cursor.fetchone()
                            if result is not None:
                               process_name = result[0]
                               get_dependent_task(process_name)
                        else:
                            # 查询指定工作流的指定任务实例ID
                            project_id = depend_item.get("projectId")
                            definition_id = depend_item.get("definitionId")

                            # 查询任务实例ID
                            sql = "SELECT id FROM t_ds_task_instance WHERE process_instance_id IN \
                                   (SELECT process_instance_id FROM t_ds_process_instance WHERE process_definition_id = {definition_id}) \
                                   AND name = '{dep_tasks}' and start_time BETWEEN '{start_time}' and '{end_time}' order by submit_time limit 1 \
                                   ".format(definition_id=definition_id, dep_tasks=dep_tasks, start_time=start_time, end_time=end_time)

                            cursor.execute(sql)
                            result = cursor.fetchone()
                            if result is not None:
                                task_id=result[0]
                                item=(project_id,definition_id,task_id)
                                #递归查找前置依赖任务的前置依赖任务
                                find_dependent_task_recursive(project_id,definition_id,task_id)
                                dependent_workflows.append(item)

    return dependent_workflows
    
#递归查找前置依赖任务的前置依赖任务
def find_dependent_task_recursive(project_id,definition_id,task_id):
    # 查询t_ds_task_instance表获取task_json字段
    with connection.cursor() as cursor:
        # 查询任务的前置任务
        sql = "SELECT task_json -> '$.preTasks' FROM t_ds_task_instance WHERE id in ({task_instance_id}) \
        and start_time BETWEEN '{start_time}' and '{end_time}' order by submit_time limit 1".format(task_instance_id=task_id,start_time=start_time, end_time=end_time)
        cursor.execute(sql)
        result = cursor.fetchone()
        if result is not None:
            task_array=result[0]
            data = json.loads(task_array, strict=False)
            pre_tasks_name = ','.join("'{0}'".format(x) for x in data)
            #查询前置任务的id和task type
            sql = "SELECT id,task_type FROM t_ds_task_instance WHERE name in ({pre_tasks_name}) \
            and start_time BETWEEN '{start_time}' and '{end_time}'".format(pre_tasks_name=pre_tasks_name,start_time=start_time, end_time=end_time)
            cursor.execute(sql)
            result = cursor.fetchall()
            if result:
                for row in result:
                    task_instance_id = row[0]
                    task_type = row[1]
                    #如果是依赖任务,执行find_dependent_workflows,否则加入到dependent_workflows
                    if task_type == dependent:
                        dependent_workflows.extend(find_dependent_workflows(task_instance_id))
                    else:
                        item=(project_id,definition_id,task_instance_id)
                        dependent_workflows.append(item)
                            


get_dependent_task(workflow_name)
workflows_set = set(dependent_workflows)
# 获取任务信息并添加到列表中
for task in workflows_set:
    task_info = get_task_info(task)
    if task_info:
        task_info_list.append(task_info)
# 输出结果
print("工作流名称：{workflow_name}".format(workflow_name=workflow_name))
# for task_info in task_info_list:
#     print("{project_name},{process_name},{task_name},{submit_time},{start_time},{end_time},{taken},{dod}"\
#     .format(project_name=task_info['project_name'],process_name=task_info['process_name'],task_name=task_info['task_name']\
#     ,submit_time=task_info['submit_time'],start_time=task_info['start_time'],end_time=task_info['end_time'],taken=task_info['taken'],dod=task_info['dod']))
starrocks_connection = pymysql.connect(**starrocks_config)
with starrocks_connection.cursor() as cursor:
    total = len(values)
    print("依赖任务总数:{total}".format(total=total))
    if total > 0:
        cursor.execute(insert_query.format(','.join(['%s'] * total)), values)

        
# 关闭数据库连接
connection.close()
starrocks_connection.close()
