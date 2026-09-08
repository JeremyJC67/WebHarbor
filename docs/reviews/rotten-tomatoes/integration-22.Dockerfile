FROM wh-review026:integrated-homepage
WORKDIR /opt/WebSyn
COPY sites/ /opt/WebSyn/
COPY websyn_start.sh /opt/websyn_start.sh
COPY control_server.py /opt/control_server.py
RUN chmod +x /opt/websyn_start.sh
RUN test -n "$(ls -A /opt/WebSyn/osu/static/images)"
RUN cd /opt/WebSyn/osu && python3 -c "\
import app; \
import os, shutil; \
os.makedirs('instance_seed', exist_ok=True); \
shutil.copy2('instance/osu.db', 'instance_seed/osu.db'); \
print('osu seed DB generated at build time.')" && rm -rf /opt/WebSyn/osu/instance

EXPOSE 8101 40000-40021
CMD ["/opt/websyn_start.sh"]
