# -*- coding: utf-8 -*-
import json
import pymysql
import sys

dt = sys.argv[1]
starrocks_config = {
    "host": "10.150.3.30",
    "port": 9030,
    "user": "ds",
    "password": "dsSR123!",
    "database": "ds",
    "charset": "utf8"
}
insert_query = """
INSERT INTO ods_task_lineage (
    project_id,dt,project_name,process_id,process_name,task_id,task_name, pre_project_id, pre_process_id,pre_task_id,pre_task_name
) VALUES {}
"""
values = []
count = 0

# 排除的工作流id
exclude_processes = '1,2,3,4,18,20,31,33'
# 连接到数据库
connection = pymysql.connect(**starrocks_config)
#查询工作流定义表
sql = "SELECT b.id as project_id,b.name as project_name ,a.id as process_id, a.name as process_name,a.process_definition_json FROM mysql_t_ds_process_definition a \
join t_ds_project b on a.project_id = b.id \
where left(a.update_time,10) <= '%s' and \
a.release_state = 1 and \
b.id not in (%s)" % (dt,exclude_processes)
print (sql)

def getTaskId(process_id, task_name):
    return "%s-%s" % (process_id,task_name)

# 遍历结果解析JSON
with connection.cursor() as cursor:
    cursor.execute(sql)
    # 遍历结果解析JSON
    for row in cursor:
        project_id = row[0]
        project_name = row[1]
        process_id = row[2]
        process_name = row[3]
        process_definition_json = row[4]
        data = json.loads(process_definition_json)
        tasks_dict = {}

        for task in data['tasks']:
            task_name = task['name']
            tasks_dict[task_name] = task

        for task_name,task in tasks_dict.items():
            type = task['type']
            if not type == 'SUB_PROCESS' and not type == 'SHELL':
                continue
            task_id = getTaskId(process_id,task_name)
            pre_project_id = None
            pre_process_id = None
            pre_task_id = None
            pre_task_name = None
            # 存在前置依赖任务
            if task.has_key('preTasks') and task['preTasks']:
                for preTaskName in task['preTasks']:
                    preTask = tasks_dict[preTaskName]
                    preTask_dependence = preTask['dependence']
                    #依赖外部工作流
                    if preTask_dependence:
                        for item in preTask_dependence['dependTaskList']:
                            for dependItem in item['dependItemList']: 
                                pre_task_name = dependItem['depTasks']
                                if dependItem.has_key('projectId'):
                                    pre_project_id = dependItem['projectId']
                                    pre_process_id = dependItem['definitionId']
                                    if not pre_task_name == 'ALL':
                                        pre_task_id = getTaskId(pre_process_id,pre_task_name)
                                else:
                                    pre_project_id = project_id
                                    pre_process_id = process_id
                                    pre_task_id = getTaskId(process_id,pre_task_name)
                                pre_task_name = dependItem['depTasks']
                                value = (project_id,dt,project_name,process_id,process_name,task_id, task_name, pre_project_id, pre_process_id,pre_task_id,pre_task_name)
                                values.append(value)
                    else:
                        pre_task_id = getTaskId(process_id,preTaskName)
                        pre_task_name = preTaskName
                        pre_project_id = project_id
                        pre_process_id = process_id
                        value = (project_id,dt,project_name,process_id,process_name, task_id,task_name, pre_project_id, pre_process_id,pre_task_id,pre_task_name)
                        values.append(value)
            else:
                value = (project_id,dt,project_name,process_id,process_name, task_id, task_name, pre_project_id, pre_process_id,pre_task_id, pre_task_name)
                values.append(value)
            # 工作流包含任务
            value = (project_id,dt,project_name,process_id,process_name, process_id, process_name, project_id, process_id,task_id, task_name)
            values.append(value)
    if values:
        tmp_values=[]
        for value in values:
            tmp_values.append(value)
            count = count + 1
            if count >= 10000:
                print("inserting %d records" % (count))
                cursor.execute(insert_query.format(','.join(['%s'] * len(tmp_values))), tmp_values)
                count = 0
                tmp_values= []
        if tmp_values:
            print("inserting %d records" % (len(tmp_values)))
            cursor.execute(insert_query.format(','.join(['%s'] * len(tmp_values))), tmp_values)
connection.close()