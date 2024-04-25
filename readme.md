# akasha-lab

# Installation
1. clone all the files in dev-ui branch to your directory
2. install akasha package(pip install akasha-terminal)
3. run fast api server (uvicorn api:app), url should be http://127.0.0.1:8000
4. run streamlit (streamlit run main.py)


# Usage
1. signup or login
2. setting openai api key in setting page
3. create new dataset in datasets page
4. create expert in experts page
5. ask question in consult page



<br/>

(optional) if you want to use.gguf models or other models from huggingface, you can download the model and put it in './model' folder in the same directory of api.py, then you can use it in consult page.



# Docker 
To use Docker to run akasha-lab, you can clone the whole project and use Dockerfile to build the image 

<br/>
<br/>

1. use git to clone or download the project 

    ```shell
    $ git clone --branch ui-dev https://github.com/iii-org/akasha.git
    $ cd akasha
    ```


2. (optional) edit install.env file 

    ```bash
    ## install.env ##
    MODEL=./model    # put the model you want to use in here
    CONFIG=./config # directory that save the dataset, expert configs
    DOCS=./docs # directory that save the document files
    IMAGE_NAME=akasha-lab
    IMAGE_VERSION=0.8

    ```


3. run the script to build image and run the container

    ``` bash 
    sudo bash install.sh

    ```


## Run Docker with default openAI Key
If you want to add default openAI API key or Azure openAI API key so that every users and use it directly, in step 2, you can add your default key in ***install.env*** file.
It will create a ***default_key.json*** file in your config directory, you can change the key value or delete it to remove the key after the akasha-lab is activated.

### openAI:

```bash
## install.env ##
MODEL=./model   
CONFIG=./config 
DOCS=./docs 
IMAGE_NAME=akasha-lab
IMAGE_VERSION=0.8
DEFAULT_OPENAI_API_KEY={your openAI key}
```



### Azure openAI:

```bash
## install.env ##
MODEL=./model   
CONFIG=./config 
DOCS=./docs 
IMAGE_NAME=akasha-lab
IMAGE_VERSION=0.8
DEFAULT_AZURE_API_KEY={your Azure key}
DEFAULT_AZURE_API_BASE={your Azure base url}
```



<br/>
<br/>




# Run Docker image

you can download the docker image from docker hub 

``` bash 
sudo docker pull ccchang0518/akasha-lab:0.8
sudo docker run -v ./model:/app/model -v ./config:/app/config -v ./docs:/app/docs -v ./chromadb:/app/chromadb -v ./accounts.yaml:/app/accounts.yaml -p 8501:8501 --name akasha-lab ccchang0518/akasha-lab:0.8

```




