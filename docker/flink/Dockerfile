FROM dinkydocker/dinky:1.1.0-flink1.18 as builder
FROM flink:1.18.1-scala_2.12-java8
ARG DLINK_VERSION="1.1.0"

ADD --chown=flink:flink  https://maven.aliyun.com/repository/central/com/starrocks/flink-connector-starrocks/1.2.9_flink-1.18/flink-connector-starrocks-1.2.9_flink-1.18.jar /opt/flink/lib/
#ADD --chown=flink:flink  https://maven.aliyun.com/repository/central/org/apache/flink/flink-sql-connector-mysql-cdc/3.1.1/flink-sql-connector-mysql-cdc-3.1.1.jar /opt/flink/lib/

#ADD --chown=flink:flink  https://maven.aliyun.com/repository/central/org/apache/flink/flink-sql-connector-kafka/3.2.0-1.18/flink-sql-connector-kafka-3.2.0-1.18.jar /opt/flink/lib/

ADD --chown=flink:flink  https://maven.aliyun.com/repository/central/mysql/mysql-connector-java/8.0.27/mysql-connector-java-8.0.27.jar /opt/flink/lib/
ADD --chown=flink:flink  https://maven.aliyun.com/repository/central/org/apache/paimon/paimon-flink-1.18/0.8.2/paimon-flink-1.18-0.8.2.jar /opt/flink/lib/
ADD --chown=flink:flink  https://repository.cloudera.com/artifactory/cloudera-repos/org/apache/flink/flink-shaded-hadoop-3-uber/3.1.1.7.2.9.0-173-9.0/flink-shaded-hadoop-3-uber-3.1.1.7.2.9.0-173-9.0.jar /opt/flink/lib/
ADD --chown=flink:flink  https://maven.aliyun.com/repository/central/org/apache/flink/flink-sql-connector-oracle-cdc/3.1.1/flink-sql-connector-oracle-cdc-3.1.1.jar /opt/flink/lib/

COPY --from=builder /opt/dinky/lib/dinky-client-base-${DLINK_VERSION}.jar /opt/flink/lib/
COPY --from=builder /opt/dinky/lib/dinky-common-${DLINK_VERSION}.jar /opt/flink/lib/
COPY --from=builder /opt/dinky/extends/flink1.18/dinky/dinky-client-1.18-${DLINK_VERSION}.jar /opt/flink/lib/
COPY --from=builder /opt/dinky/jar/dinky-app-1.18-${DLINK_VERSION}-jar-with-dependencies.jar /opt/flink/lib/
COPY --from=builder /opt/dinky/extends/flink1.18/flink/flink-table-planner_2.12-1.18.1.jar /opt/flink/lib/
RUN rm -rf /opt/flink/lib/flink-table-planner-loader-*.jar

#ADD --chown=flink:flink  https://maven.aliyun.com/repository/central/com/oracle/database/xml/xdb/19.3.0.0/xdb-19.3.0.0.jar /opt/flink/lib/
ADD --chown=flink:flink  https://repo1.maven.org/maven2/commons-cli/commons-cli/1.8.0/commons-cli-1.8.0.jar /opt/flink/lib/
RUN mkdir -p /etc/hive/conf && mkdir -p /etc/hadoop/conf && chown -R flink:flink /etc/hive/conf /etc/hadoop/conf
COPY --chown=flink:flink ./hive-site.xml /etc/hive/conf
COPY --chown=flink:flink ./hdfs-site.xml ./core-site.xml /etc/hadoop/conf
ADD --chown=flink:flink https://repo1.maven.org/maven2/org/apache/paimon/paimon-flink-action/0.8.2/paimon-flink-action-0.8.2.jar /opt/flink/lib/
ADD --chown=flink:flink https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-hive-2.3.9_2.12/1.18.1/flink-sql-connector-hive-2.3.9_2.12-1.18.1.jar /opt/flink/lib/
ADD --chown=flink:flink  https://maven.aliyun.com/repository/central/org/apache/flink/flink-connector-jdbc/3.2.0-1.18/flink-connector-jdbc-3.2.0-1.18.jar /opt/flink/lib/
#ADD --chown=flink:flink https://repo1.maven.org/maven2/com/oracle/database/jdbc/ojdbc6/11.2.0.4/ojdbc6-11.2.0.4.jar /opt/flink/lib/
ADD --chown=flink:flink https://repo1.maven.org/maven2/com/oracle/database/nls/orai18n/19.3.0.0/orai18n-19.3.0.0.jar /opt/flink/lib/
COPY --chown=flink:flink ./ojdbc8-19.3.0.0.jar /opt/flink/lib/
COPY --chown=flink:flink ./flink-sql-connector-oracle-cdc-3.1.1.jar /opt/flink/lib/
