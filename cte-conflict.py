#coding=utf-8
import pymysql
import sys
connection = pymysql.connect(
        host='10.150.3.30',
        port=9030,
        user='starrocks',
        password='yiliSR123!',
        database='tmp'
    )
cte_1 = r"""
with tmp_fact_csq_nf_daily_booked1_vp as (
        SELECT  so.line_request_date    AS order_date_id
               ,so.line_request_date_hour_id as hour_id
               ,so.line_request_date_detail as date_detail
               ,so.dealer_wid   AS dealer_wid --客户编号
               ,so.dealer_code --经销商编码
               ,so.dealer_name --经销商名称
               ,so.ordered_item --产品
               ,so.order_number --订单编号
               ,so.area_wid --区域编码代理键 
               ,so.big_area_name --大区名称 
               ,so.area_name --区域编码 
               ,so.cities_name --城市群编码 
               ,so.city_name --城市编码 
               ,0 as types --类型
               ,SUM(so.cur_ordered_ton) AS cur_ordered_ton --当日订单吨量
               ,SUM(so.cur_ordered_box) AS cur_ordered_box --当日订单件数
               ,SUM(so.bf_dis_amt / (1 + (coalesce(zmer.tax_rate_percentage,0) / 100))) cur_ordered_amt --订单金额 要这个
        FROM tmp.tmp_pj_csq_erp_so_data so --对标 rtm_dm.pj_csq_erp_so_data
        INNER JOIN ods.d_pty_mdm_dealer_main t2
        ON so.dealer_code = t2.acct_code
        INNER JOIN ods.d_pty_mdm_dealer_sub sub
        ON t2.sys_row_id = sub.dealer_rela_row_id AND sub.biz_unit_cd = 'NF'  and (sub.e_commerce <> 'Y' or sub.e_commerce is null)
        LEFT JOIN ods.d_par_client_tax_rate zmer --客户税率
        ON so.tax_code = zmer.tax_rate_code AND zmer.active_flag = '1' AND coalesce(zmer.default_rate_flag, '1') = '1' AND zmer.tax_rate_type_code = 'PERCENTAGE'
        WHERE 1 = 1
        AND so.order_type_id = 'R' --外部订单 和 大区 非默认
        AND so.unit_selling_price > 0 --产品价格
        AND so.attribute1 <> 'ENTERED'
        AND so.big_area_name <> '默认' --大区
        AND so.big_area_name is not null
        AND so.line_request_date >= date_format(current_date(),'%Y%m01') --日期限制
        GROUP BY  so.line_request_date --日期
                 ,so.line_request_date_hour_id
                 ,so.line_request_date_detail
                 ,so.dealer_wid
                 ,so.dealer_code --客户编号
                 ,so.dealer_name --经销商名称
                 ,so.ordered_item
                 ,so.order_number
                 ,so.area_wid --区域编码代理键 
                 ,so.big_area_name --大区名称 
                 ,so.area_name --区域编码 
                 ,so.cities_name --城市群编码 
                 ,so.city_name --城市编码 
        union all
        --电商客户取日期取actual_shipment_date
        SELECT  so.actual_shipment_date AS order_date_id
               ,so.actual_shipment_date_hour_id as hour_id
               ,so.actual_shipment_date_detail as date_detail
               ,so.dealer_wid   AS dealer_wid --客户编号
               ,so.dealer_code --经销商编码
               ,so.dealer_name --经销商名称
               ,so.ordered_item --产品
               ,so.order_number --订单编号
               ,so.area_wid --区域编码代理键 
               ,so.big_area_name --大区名称 
               ,so.area_name --区域编码 
               ,so.cities_name --城市群编码 
               ,so.city_name --城市编码 
               ,1 as types --产品
               ,SUM(so.cur_ordered_ton) AS cur_ordered_ton --当日订单吨量
               ,SUM(so.cur_ordered_box) AS cur_ordered_box --当日订单件数
               ,SUM(so.bf_dis_amt / (1 + (coalesce(zmer.tax_rate_percentage,0) / 100))) cur_ordered_amt --订单金额 要这个
        FROM tmp.tmp_pj_csq_erp_so_data so --对标 rtm_dm.pj_csq_erp_so_data
        INNER JOIN ods.d_pty_mdm_dealer_main t2
        ON so.dealer_code = t2.acct_code
        INNER JOIN ods.d_pty_mdm_dealer_sub sub
        ON t2.sys_row_id = sub.dealer_rela_row_id AND sub.biz_unit_cd = 'NF'  and sub.e_commerce = 'Y' --电商取Y
        LEFT JOIN ods.d_par_client_tax_rate zmer --客户税率
        ON so.tax_code = zmer.tax_rate_code AND zmer.active_flag = '1' AND coalesce(zmer.default_rate_flag, '1') = '1' AND zmer.tax_rate_type_code = 'PERCENTAGE'
        where 1 = 1
        AND so.order_type_id = 'R' --外部订单 和 大区 非默认
        AND so.unit_selling_price > 0 --产品价格
        AND so.attribute1 <> 'ENTERED'
        AND so.big_area_name <> '默认' --大区
        AND so.big_area_name is not null
        AND so.actual_shipment_date >= date_format(current_date(),'%Y%m01') --日期限制
        GROUP BY  so.actual_shipment_date --日期
                 ,so.actual_shipment_date_hour_id
                 ,so.dealer_wid
                 ,so.dealer_code --客户编号
                 ,so.dealer_name --经销商名称
                 ,so.ordered_item
                 ,so.actual_shipment_date_detail
                 ,so.order_number
                 ,so.area_wid --区域编码代理键 
                 ,so.big_area_name --大区名称 
                 ,so.area_name --区域编码 
                 ,so.cities_name --城市群编码 
                 ,so.city_name --城市编码 
        )
        SELECT  count(*)
        FROM tmp_fact_csq_nf_daily_booked1_vp t1 --对标 tmp.fact_csq_nf_daily_booked1_vp
        -- LEFT JOIN ods.dm_dealer_region_rel drr
        -- ON t1.customer_number = drr.dealer_id AND drr.dept_cd = 'NF'
        -- LEFT JOIN ods.dm_sale_region ds
        -- ON drr.manage_region_id = ds.sale_region_id AND ds.dept_cd = 'NF'
        where t1.order_date_id >= date_format(current_date(),'%Y%m01') --日期限制
        ;
"""

cte_2 = """with tmp_fact_csq_nf_daily_booked1_vp as (
        SELECT  so.line_request_date    AS order_date_id
               ,so.line_request_date_hour_id as hour_id
               ,so.line_request_date_detail as date_detail
               ,so.dealer_wid   AS dealer_wid --客户编号
               ,so.dealer_code --经销商编码
               ,so.dealer_name --经销商名称
               ,so.ordered_item --产品
               ,so.order_number --订单编号
               ,so.area_wid --区域编码代理键 
               ,so.big_area_name --大区名称 
               ,so.area_name --区域编码 
               ,so.cities_name --城市群编码 
               ,so.city_name --城市编码 
               ,0 as types --类型
               ,SUM(so.cur_ordered_ton) AS cur_ordered_ton --当日订单吨量
               ,SUM(so.cur_ordered_box) AS cur_ordered_box --当日订单件数
               ,SUM(so.bf_dis_amt / (1 + (coalesce(zmer.tax_rate_percentage,0) / 100))) cur_ordered_amt --订单金额 要这个
        FROM tmp.tmp_pj_csq_erp_so_data_cr so --对标 rtm_dm.pj_csq_erp_so_data
        INNER JOIN ods.d_pty_mdm_dealer_main t2
        ON so.dealer_code = t2.acct_code
        INNER JOIN ods.d_pty_mdm_dealer_sub sub
        ON t2.sys_row_id = sub.dealer_rela_row_id AND sub.biz_unit_cd = 'CR'  and (sub.e_commerce <> 'Y' or sub.e_commerce is null)
        LEFT JOIN ods.d_par_client_tax_rate zmer --客户税率
        ON so.tax_code = zmer.tax_rate_code AND zmer.active_flag = '1' AND coalesce(zmer.default_rate_flag, '1') = '1' AND zmer.tax_rate_type_code = 'PERCENTAGE'
        WHERE 1 = 1
        AND so.order_type_id = 'R' --外部订单 和 大区 非默认
        AND so.unit_selling_price > 0 --产品价格
        AND so.attribute1 <> 'ENTERED'
        AND so.big_area_name <> '默认' --大区
        AND so.big_area_name is not null
        AND so.line_request_date >= date_format(current_date(),'%Y%m01') --日期限制
        GROUP BY  so.line_request_date --日期
                 ,so.line_request_date_hour_id
                 ,so.line_request_date_detail
                 ,so.dealer_wid
                 ,so.dealer_code --客户编号
                 ,so.dealer_name --经销商名称
                 ,so.ordered_item
                 ,so.order_number
                 ,so.area_wid --区域编码代理键 
                 ,so.big_area_name --大区名称 
                 ,so.area_name --区域编码 
                 ,so.cities_name --城市群编码 
                 ,so.city_name --城市编码 
        union all
        --电商客户取日期取actual_shipment_date
        SELECT  so.actual_shipment_date AS order_date_id
               ,so.actual_shipment_date_hour_id as hour_id
               ,so.actual_shipment_date_detail as date_detail
               ,so.dealer_wid   AS dealer_wid --客户编号
               ,so.dealer_code --经销商编码
               ,so.dealer_name --经销商名称
               ,so.ordered_item --产品
               ,so.order_number --订单编号
               ,so.area_wid --区域编码代理键 
               ,so.big_area_name --大区名称 
               ,so.area_name --区域编码 
               ,so.cities_name --城市群编码 
               ,so.city_name --城市编码 
               ,1 as types --产品
               ,SUM(so.cur_ordered_ton) AS cur_ordered_ton --当日订单吨量
               ,SUM(so.cur_ordered_box) AS cur_ordered_box --当日订单件数
               ,SUM(so.bf_dis_amt / (1 + (coalesce(zmer.tax_rate_percentage,0) / 100))) cur_ordered_amt --订单金额 要这个
        FROM tmp.tmp_pj_csq_erp_so_data_cr so --对标 rtm_dm.pj_csq_erp_so_data
        INNER JOIN ods.d_pty_mdm_dealer_main t2
        ON so.dealer_code = t2.acct_code
        INNER JOIN ods.d_pty_mdm_dealer_sub sub
        ON t2.sys_row_id = sub.dealer_rela_row_id AND sub.biz_unit_cd = 'CR'  and sub.e_commerce = 'Y' --电商取Y
        LEFT JOIN ods.d_par_client_tax_rate zmer --客户税率
        ON so.tax_code = zmer.tax_rate_code AND zmer.active_flag = '1' AND coalesce(zmer.default_rate_flag, '1') = '1' AND zmer.tax_rate_type_code = 'PERCENTAGE'
        where 1 = 1
        AND so.order_type_id = 'R' --外部订单 和 大区 非默认
        AND so.unit_selling_price > 0 --产品价格
        AND so.attribute1 <> 'ENTERED'
        AND so.big_area_name <> '默认' --大区
        AND so.big_area_name is not null
        AND so.actual_shipment_date >= date_format(current_date(),'%Y%m01') --日期限制
        GROUP BY  so.actual_shipment_date --日期
                 ,so.actual_shipment_date_hour_id
                 ,so.dealer_wid
                 ,so.dealer_code --客户编号
                 ,so.dealer_name --经销商名称
                 ,so.ordered_item
                 ,so.actual_shipment_date_detail
                 ,so.order_number
                 ,so.area_wid --区域编码代理键 
                 ,so.big_area_name --大区名称 
                 ,so.area_name --区域编码 
                 ,so.cities_name --城市群编码 
                 ,so.city_name --城市编码 
        )
        SELECT  count(*)
        FROM tmp_fact_csq_nf_daily_booked1_vp t1 --对标 tmp.fact_csq_nf_daily_booked1_vp
        -- LEFT JOIN ods.dm_dealer_region_rel drr
        -- ON t1.customer_number = drr.dealer_id AND drr.dept_cd = 'NF'
        -- LEFT JOIN ods.dm_sale_region ds
        -- ON drr.manage_region_id = ds.sale_region_id AND ds.dept_cd = 'NF'
        where t1.order_date_id >= date_format(current_date(),'%Y%m01') --日期限制
        ;"""
with connection.cursor() as cursor:
  cursor.execute("select count(*) from tmp.cte_1")
  result_1 = cursor.fetchone()
  cnt =  result_1[0]
  if cnt > 0:
    print "cte_1 count",cnt
  else:
    cursor.execute(cte_1)
    result = cursor.fetchone()
    cte_cnt = result[0]
    print "tmp.cte_1 count:%s, cte tmp table count:%s" % (cnt,cte_cnt)
    sys.exit(-1)
  cursor.execute("select count(*) from tmp.cte_2")
  result_1 = cursor.fetchone()
  cnt =  result_1[0]
  if cnt > 0:
    print "cte_2 count",cnt
  else:
    cursor.execute(cte_2)
    result = cursor.fetchone()
    cte_cnt = result[0]
    print "tmp.cte_2 count:%s, cte tmp table count:%s" % (cnt,cte_cnt)
    sys.exit(-1)