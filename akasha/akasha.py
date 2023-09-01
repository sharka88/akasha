import pathlib
import time
from tqdm import tqdm
import torch
from langchain.chains.question_answering import load_qa_chain, LLMChain
from langchain import PromptTemplate
from langchain.schema import Document
import akasha.helper as helper
import akasha.search as search
import akasha.format as format
import akasha.prompts as prompts
import datetime
from dotenv import load_dotenv
load_dotenv(pathlib.Path().cwd()/'.env') 

def get_response(doc_path:str, prompt:str = "", embeddings:str = "openai:text-embedding-ada-002", chunk_size:int=1000\
                 , model:str = "openai:gpt-3.5-turbo", verbose:bool = False, topK:int = 2, threshold:float = 0.2,\
                 language:str = 'ch' , search_type:str = 'merge', compression:bool = False, record_exp:str = "", \
                 system_prompt:str = "", max_token:int=3000 )->str:
    """input the documents directory path and question, will first store the documents
    into vectors db (chromadb), then search similar documents based on the prompt question.
    llm model will use these documents to generate the response of the question.

    Args:
        **doc_path (str)**: documents directory path\n
        **prompt (str, optional)**: question you want to ask. Defaults to "".\n
        **embeddings (str, optional)**: the embeddings used in query and vector storage. Defaults to "text-embedding-ada-002".\n
        **chunk_size (int, optional)**: the text length to split document to multiple chunks. Defaults to 1000.\n
        **model (str, optional)**: llm model to use. Defaults to "gpt-3.5-turbo".\n
        **verbose (bool, optional)**: show log texts or not. Defaults to False.\n
        **topK (int, optional)**: search top k number of similar documents. Defaults to 2.\n
        **threshold (float, optional)**: the similarity threshold of searching. Defaults to 0.2.\n
        **language (str, optional)**: the language of documents and prompt, use to make sure docs won't exceed
            max token size of llm input.\n
        **search_type (str, optional)**: search type to find similar documents from db, default 'merge'.
            includes 'merge', 'mmr', 'svm', 'tfidf'.\n
        **compression (bool)**: compress the relevant documents or not.\n
        **record_exp (str, optional)**: use aiido to save running params and metrics to the remote mlflow or not if record_exp not empty, and set 
            record_exp as experiment name.  default ''.\n
        **system_prompt (str, optional)**: system prompt for llm to generate response. Defaults to "".\n
        **max_token (int, optional)**: max token size of llm input. Defaults to 3000.\n
    Returns:
        str: llm output str\n
    """
    
    start_time = time.time()
    logs = ["\n\n-----------------get_response----------------------\n"]
    params = format.handle_params(model, embeddings, chunk_size, search_type, topK, threshold, language, compression)
    embeddings_name = embeddings
    embeddings = helper.handle_embeddings(embeddings, logs, verbose)
    model = helper.handle_model(model, logs, verbose)
    logs.append(datetime.datetime.now().strftime( "%Y/%m/%d, %H:%M:%S"))
    

    db = helper.create_chromadb(doc_path, logs, verbose, embeddings, embeddings_name, chunk_size)

    if db is None:
        info = "document path not exist\n"
        print(info)
        logs.append(info)
        return ""


    
    docs, tokens = search.get_docs(db, embeddings, prompt, topK, threshold, language, search_type, verbose,\
                     logs, model, compression, max_token)
    if docs is None:
        return ""
    
    doc_length = helper.get_docs_length(language, docs)
    
    chain = load_qa_chain(llm=model, chain_type="stuff",verbose=False)
    if verbose:
        print(docs)
    logs.append("\n\ndocuments: \n\n" + ''.join([doc.page_content for doc in docs]))
    
    res = chain.run(input_documents=docs, question=system_prompt + prompt)
    res =  helper.sim_to_trad(res)
    response = res.split("Finished chain.")
    
    
    if verbose:
        print(response)
    logs.append("\n\nresponse:\n\n"+ response[-1])
    
    end_time = time.time()
    if record_exp != "":    
        metrics = format.handle_metrics(doc_length, end_time - start_time, tokens)
        table = format.handle_table(prompt, docs, response)
        model.get_num_tokens(''.join([doc.page_content for doc in docs]))
        aiido_upload(record_exp, params, metrics, table)
    helper.save_logs(logs)
    return response[-1]









def chain_of_thought(doc_path:str, prompt:list, embeddings:str = "openai:text-embedding-ada-002", chunk_size:int=1000\
                 , model:str = "openai:gpt-3.5-turbo", verbose:bool = False, topK:int = 2, threshold:float = 0.2,\
                 language:str = 'ch' , search_type:str = 'merge',  compression:bool = False, record_exp:str = "", system_prompt:str=""\
                 , max_token:int=3000)->str:
    """input the documents directory path and question, will first store the documents
        into vectors db (chromadb), then search similar documents based on the prompt question.
        llm model will use these documents to generate the response of the question.

        In chain_of_thought function, you can separate your question into multiple small steps so that llm can have better response.
        chain_of_thought function will use all responses from the previous prompts, and combine the documents search from current prompt to generate
        response.
        

    Args:
        **doc_path (str)**: documents directory path\n
        **prompt (str, optional)**: question you want to ask. Defaults to "".\n
        **embeddings (str, optional)**: the embeddings used in query and vector storage. Defaults to "text-embedding-ada-002".\n
        **chunk_size (int, optional)**: the text length to split document to multiple chunks. Defaults to 1000.\n
        **model (str, optional)**: llm model to use. Defaults to "gpt-3.5-turbo".\n
        **verbose (bool, optional)**: show log texts or not. Defaults to False.\n
        **topK (int, optional)**: search top k number of similar documents. Defaults to 2.\n
        **threshold (float, optional)**: the similarity threshold of searching. Defaults to 0.2.\n
        **language (str, optional)**: the language of documents and prompt, use to make sure docs won't exceed
            max token size of llm input.\n
        **search_type (str, optional)**: search type to find similar documents from db, default 'merge'.
            includes 'merge', 'mmr', 'svm', 'tfidf'.\n
        **compression (bool)**: compress the relevant documents or not.\n
        **record_exp (str, optional)**: use aiido to save running params and metrics to the remote mlflow or not if record_exp not empty, and set 
            record_exp as experiment name.  default ''.\n
        **system_prompt (str, optional)**: system prompt for llm to generate response. Defaults to "".\n
        **max_token (int, optional)**: max token size of llm input. Defaults to 3000.\n
        
    Returns:
        str: llm output str
    """
    start_time = time.time()
    logs = ["\n\n---------------chain_of_thought------------------------\n"]
    params = format.handle_params(model, embeddings, chunk_size, search_type, topK, threshold, language, compression)
    embeddings_name = embeddings
    embeddings = helper.handle_embeddings(embeddings, logs, verbose)
    model = helper.handle_model(model, logs, verbose)
    logs.append(datetime.datetime.now().strftime( "%Y/%m/%d, %H:%M:%S"))
    

    db = helper.create_chromadb(doc_path, logs, verbose, embeddings, embeddings_name, chunk_size)

    if db is None:
        info = "document path not exist\n"
        print(info)
        logs.append(info)
        return ""

    chain = load_qa_chain(llm=model, chain_type="stuff",verbose=False)

    
    ori_docs = []
    doc_length = 0
    tokens = 0
    pre_result = []
    for i in range(len(prompt)):

        docs, docs_token = search.get_docs(db, embeddings, prompt[i], topK, threshold, language, search_type,\
                            verbose, logs, model, compression, max_token)
        
        doc_length += helper.get_docs_length(language, docs)
        tokens += docs_token
        ori_docs.extend(docs)
        if verbose:
            print(docs)
        logs.append("\n\ndocuments: \n\n" + ''.join([doc.page_content for doc in docs]))



        res = chain.run(input_documents=docs + pre_result, question=system_prompt + prompt[i])
        res = helper.sim_to_trad(res)
        response = res.split("Finished chain.")
        print(response)

        logs.append("\n\nresponse:\n\n"+ response[-1])
        pre_result.append(Document(page_content=''.join(response)))
        
    

    end_time = time.time()    
    if record_exp != "":    
        metrics = format.handle_metrics(doc_length, end_time - start_time,tokens)
        table = format.handle_table('\n\n'.join([p for p in prompt]), ori_docs, response)
        aiido_upload(record_exp, params, metrics, table)
    helper.save_logs(logs)
    return response[-1]




def aiido_upload(exp_name, params:dict={}, metrics:dict={}, table:dict={}, path_name:str=""):
    """upload params_metrics, table to mlflow server for tracking.

    Args:
        **exp_name (str)**: experiment name on the tracking server, if not found, will create one .\n
        **params (dict, optional)**: parameters dictionary. Defaults to {}.\n
        **metrics (dict, optional)**: metrics dictionary. Defaults to {}.\n
        **table (dict, optional)**: table dictionary, used to compare text context between different runs in the experiment. Defaults to {}.\n
    """
    import aiido
    
    if "model" not in params or "embeddings" not in params:
        aiido.init(experiment=exp_name, run = path_name)
        
    else:
        mod = params["model"].split(':')
        emb = params["embeddings"].split(':')[0]
        sea = params["search_type"]
        aiido.init(experiment=exp_name, run = emb + '-' + sea + '-' + '-'.join(mod))
    
    aiido.log_params_and_metrics(params=params, metrics=metrics)


    if len(table) > 0:
        import mlflow
        mlflow.log_table(table,"table.json")
    aiido.end_run()
    return




def test_performance(q_file:str, doc_path:str, embeddings:str = "openai:text-embedding-ada-002", chunk_size:int=1000\
                 , model:str = "openai:gpt-3.5-turbo", topK:int = 2, threshold:float = 0.2,\
                 language:str = 'ch' , search_type:str = 'merge', compression:bool = False, record_exp:str = "", max_token:int=3000 ):
    """input a txt file includes list of single choice questions and the answer, will test all of the questions and return the
    correct rate of this parameters(model, embeddings, search_type, chunk_size)\n
    the format of q_file(.txt) should be one line one question, and the possibles answers and questions are separate by space,
    the last one is which possisble answers is the correct answer, for example, the file should look like: \n
        "What is the capital of Taiwan?" Taipei  Kaohsiung  Taichung  Tainan     1
        何者是台灣的首都?  台北 高雄 台中 台南   1
    
    Args:
        **q_file (str)**: the file path of the question file\n
        **doc_path (str)**: documents directory path\n
        **embeddings (str, optional)**: the embeddings used in query and vector storage. Defaults to "text-embedding-ada-002".\n
        **chunk_size (int, optional)**: the text length to split document to multiple chunks. Defaults to 1000.\n
        **model (str, optional)**: llm model to use. Defaults to "gpt-3.5-turbo".\n
        **topK (int, optional)**: search top k number of similar documents. Defaults to 2.\n
        **threshold (float, optional)**: the similarity threshold of searching. Defaults to 0.2.\n
        **language (str, optional)**: the language of documents and prompt, use to make sure docs won't exceed
            max token size of llm input.\n
        **search_type (str, optional)**: search type to find similar documents from db, default 'merge'.
            includes 'merge', 'mmr', 'svm', 'tfidf', 'knn'.\n
        **compression (bool)**: compress the relevant documents or not.\n
        **record_exp (str, optional)**: use aiido to save running params and metrics to the remote mlflow or not if record_exp not empty, and set 
            record_exp as experiment name.  default ''.\n
        **max_token (int, optional)**: max token size of llm input. Defaults to 3000.\n
        
    Returns:
        float: the correct rate of all questions
    """
    query_list = helper.get_question_from_file(q_file)
    correct_count = 0
    total_question = len(query_list)
    doc_length = 0
    tokens = 0
    verbose = False
    start_time = time.time()
    logs = ["\n\n---------------test_performance------------------------\n"]
    table = {}
    params = format.handle_params(model, embeddings, chunk_size, search_type, topK, threshold, language, compression)
    embeddings_name = embeddings
    embeddings = helper.handle_embeddings(embeddings, logs, verbose)
    model = helper.handle_model(model, logs, verbose)
    logs.append(datetime.datetime.now().strftime( "%Y/%m/%d, %H:%M:%S"))
    

    db = helper.create_chromadb(doc_path, logs, verbose, embeddings, embeddings_name, chunk_size)

    if db is None:
        info = "document path not exist\n"
        logs.append(info)
        return ""


    for question in tqdm(query_list,total=total_question,desc="Run Question Set"):
        
        query, ans = prompts.format_question_query(question)

        docs, docs_token = search.get_docs(db, embeddings, query, topK, threshold, language, search_type, verbose,\
                     logs, model, compression, max_token)
        doc_length += helper.get_docs_length(language, docs)
        tokens += docs_token
        query_with_prompt = prompts.format_llama_json(query)
        

        try:
            chain = load_qa_chain(llm=model, chain_type="stuff",verbose=False)
            response = chain.run(input_documents = docs, question = query_with_prompt)
            response = helper.sim_to_trad(response)
            response = response.split("Finished chain.")
        except:
            print("running model error\n")
            response = ["running model error"]
            torch.cuda.empty_cache()

        logs.append("\n\ndocuments: \n\n" + ''.join([doc.page_content for doc in docs]))
        logs.append("\n\nresponse:\n\n"+ response[-1])
        
        new_table = format.handle_table(query, docs, response)
        for key in new_table:
            if key not in table:
                table[key] = []
            table[key].append(new_table[key])
                

        result = helper.extract_result(response)

        if str(result) == str(ans):
            correct_count += 1
    end_time = time.time()

    if record_exp != "":    
        metrics = format.handle_metrics(doc_length, end_time - start_time, tokens)
        metrics['correct_rate'] = correct_count/total_question
        aiido_upload(record_exp, params, metrics, table)
    helper.save_logs(logs)

    return correct_count/total_question , tokens



def detect_exploitation(texts:str, model:str = "openai:gpt-3.5-turbo", verbose:bool = False, record_exp:str = ""):
    """ check the given texts have harmful or sensitive information

    Args:
        **texts (str)**: texts that we want llm to check.\n
        **model (str, optional)**: llm model name. Defaults to "openai:gpt-3.5-turbo".\n
        **verbose (bool, optional)**: show log texts or not. Defaults to False.\n
        **record_exp (str, optional)**: use aiido to save running params and metrics to the remote mlflow or not if record_exp not empty, and set 
            record_exp as experiment name.  default ''.\n

    Returns:
        str: response from llm
    """

    logs = []
    model = helper.handle_model(model, logs, verbose)
    sys_b, sys_e = "<<SYS>>\n", "\n<</SYS>>\n\n"
    system_prompt = "[INST]" + sys_b +\
    "check if below texts have any of Ethical Concerns, discrimination, hate speech, "+\
    "illegal information, harmful content, Offensive Language, or encourages users to share or access copyrighted materials"+\
    " And return true or false. Texts are: " + sys_e  + "[/INST]"
       
    template = system_prompt+""" 
    
    Texts: {texts}
    Answer: """
    prompt = PromptTemplate(template=template, input_variables={"texts"})
    response = LLMChain(prompt=prompt,llm=model).run(texts)
    print(response)
    return response





def optimum_combination(q_file:str, doc_path:str, embeddings_list:list = ["openai:text-embedding-ada-002"], chunk_size_list:list=[500]\
                 , model_list:list = ["openai:gpt-3.5-turbo"], topK_list:list = [2], threshold:float = 0.2,\
                 language:str = 'ch' , search_type_list:list = ['merge','svm','tfidf','mmr'], compression:bool = False, record_exp:str = ""\
                    , max_token:int=3000):
    """test all combinations of giving lists, and run test_performance to find parameters of the best result.

    Args:
        **q_file (str)**: the file path of the question file\n
        **doc_path (str)**: documents directory path\n
        **embeddings_list (_type_, optional)**: list of embeddings models. Defaults to ["openai:text-embedding-ada-002"].\n
        **chunk_size_list (list, optional)**: list of chunk sizes. Defaults to [500].\n
        **model_list (_type_, optional)**: list of models. Defaults to ["openai:gpt-3.5-turbo"].\n
        **topK_list (list, optional)**: list of topK. Defaults to [2].\n
        **threshold (float, optional)**: the similarity threshold of searching. Defaults to 0.2.\n
        **search_type_list (list, optional)**: list of search types, currently have "merge", "svm", "knn", "tfidf", "mmr". Defaults to ['merge','svm','tfidf','mmr'].
        **compression (bool)**: compress the relevant documents or not.\n
        **record_exp (str, optional)**: use aiido to save running params and metrics to the remote mlflow or not if record_exp not empty, and set 
            record_exp as experiment name.  default ''.\n
        **max_token (int, optional)**: max token size of llm input. Defaults to 3000.\n
        
    Returns:
        (list,list): return best score combination and best cost-effective combination
    """
    logs = ["\n\n----------------optimum_combination-----------------------\n"]
    start_time = time.time()
    combinations = helper.get_all_combine(embeddings_list, chunk_size_list, model_list, topK_list, search_type_list)
    progress = tqdm(len(combinations),total = len(combinations), desc="RUN LLM")
    print("\n\ntotal combinations: ", len(combinations))
    result_list = []
    bcr = 0.0
    for embed, chk, mod, tK, st in combinations:
        progress.update(1)
        cur_correct_rate, tokens = test_performance(q_file, doc_path, embeddings=embed, chunk_size=chk, model=mod, topK=tK, threshold=threshold,\
                            language=language, search_type=st, compression=compression, record_exp=record_exp, max_token=max_token) 
        bcr = max(bcr,cur_correct_rate)
        cur_tup = (cur_correct_rate, cur_correct_rate/tokens, embed, chk, mod, tK, st)
        result_list.append(cur_tup)
        
    progress.close()


    ### record logs ###
    print("Best correct rate: ", "{:.3f}".format(bcr))
    score_comb = "Best score combination: \n"
    print(score_comb)
    logs.append(score_comb)
    bs_combination = helper.get_best_combination(result_list, 0,logs)


    print("\n\n")
    cost_comb = "Best cost-effective: \n"
    print(cost_comb)
    logs.append(cost_comb)
    bc_combination = helper.get_best_combination(result_list, 1,logs)



   
    end_time = time.time()
    format_time = "time spend: " + "{:.3f}".format(end_time-start_time)
    print( format_time )
    logs.append( format_time )
    helper.save_logs(logs)
    return bs_combination, bc_combination



