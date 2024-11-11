FROM ccchang0518/akasha-lab-builder:0.8
LABEL maintainer=chih-chuan-chang<ccchang@iii.org.tw>

WORKDIR /app
COPY api.py /app
COPY start.sh /app
COPY api_utils.py /app
COPY main.py /app
COPY utils.py /app
COPY ./views /app/views
COPY ./routers /app/routers
COPY requirements.txt /app
RUN chmod u+x *.sh
EXPOSE 8000

RUN python -m pip install --upgrade pip && python -m pip install -r requirements.txt
ENV PORT=8501
ENV PREFIX=akasha-lab
ENV USE_PREFIX=false
ENV ANONYMIZED_TELEMETRY=false
EXPOSE $PORT
CMD ["sh", "-c", "if [ \"$USE_PREFIX\" = \"true\" ]; then \
    nohup /bin/bash -c \"./start.sh &\" && streamlit run main.py --server.maxUploadSize 200000 --server.port 8501 --browser.serverAddress 0.0.0.0 --server.headless true --server.baseUrlPath /${PREFIX}/; \
else \
    nohup /bin/bash -c \"./start.sh &\" && streamlit run main.py --server.maxUploadSize 200000 --server.port 8501 --browser.serverAddress 0.0.0.0 --server.headless true; \
fi"]
#ENTRYPOINT nohup /bin/bash -c "./start.sh &" && streamlit run main.py --server.maxUploadSize 200000  --server.port 8501 --browser.serverAddress 0.0.0.0 --server.headless true --server.baseUrlPath ${baseUrl}