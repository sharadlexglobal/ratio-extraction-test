FROM postgres:17-alpine
COPY migrate.sh /migrate.sh
COPY index.sql /index.sql
COPY run.sh /run.sh
RUN chmod +x /migrate.sh /run.sh
CMD ["/bin/sh", "/run.sh"]
