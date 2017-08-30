import logging
import json
import time
import re
#import nltk
#from nltk.corpus import stopwords
from nltk.stem.snowball import SnowballStemmer

import pystache
from flask import make_response, request
from flask_login import current_user
from flask_restful import abort
from redash import models, settings, utils
from redash.tasks import QueryTask, record_event
from redash.permissions import require_permission, not_view_only, has_access, require_access, view_only
from redash.handlers.base import BaseResource, get_object_or_404
from redash.utils import collect_query_parameters, collect_parameters_from_request, gen_query_hash
from redash.tasks.queries import enqueue_query
import redash.utils.spell_checker as sc

from redash.handlers.visualizations import VisualizationListResource
#from redash.handlers.queries import QueryListResource


def error_response(message):
    return {'job': {'status': 4, 'error': message}}, 400

def get_mappings():
    mapper = {}
    sentences = []
    sqls = []

    sentences.append("show me numbers of millennials who showed interest in auto and rental insurances in last month")
    sentences.append("show me numbers of millennials who showed interest in home insurances in last month")
    sentences.append("show me numbers of 40 year and above looking to purchase umbrella insurance")
    sentences.append("how many usaa families are not engaging in email marketing campaign across california region in 2016")
    sentences.append("how many usaa families are engaging in monthly email marketing campaign across california region in 2016")
    sentences.append("which newsletter getting highest engagements in 2016")
    sentences.append("show me usaa families who has purchased small business insurance across texas")
    sentences.append("transaction volume of renewal transactions in 2016 across states")
    sentences.append("how many requests for auto loan came through last year search engine marketing campaigns?")
    
    sentences.append("show number of transactions for each product")
    sentences.append("get number of transactions for Auto Insurance and Rental Insurance grouped by month")
    sentences.append("show me number of transactions for each state as a map")


    sqls.append("select count(*) from (select f.family_id from families f inner join transactions t on f.family_id = t.family_id inner join finance_products p on p.prod_id = t.prod_id where prod_name='Rental Insurance' or prod_name='Auto Insurance' and act_date > '2017-06-01' and dob > '1990-01-01' group by f.family_id having count(distinct p.prod_id)>1) as A;")
    sqls.append("select count(*) from families f inner join transactions t on f.family_id = t.family_id inner join finance_products p on p.prod_id = t.prod_id where prod_name='Home Insurance' and act_date > '2017-06-01' and dob > '1990-01-01';")
    sqls.append("select count(*) from families f inner join transactions t on f.family_id = t.family_id inner join finance_products p on p.prod_id = t.prod_id where prod_name='Umbrella Insurance' and dob < '1977-01-01';")
    sqls.append("select count(*) from families where family_id not in (select family_id from transactions where act_date > '2016-01-01' and act_date < '2016-12-31' and marketing='email') and state='california';")
    sqls.append("select count(*) from families where family_id in (select family_id from transactions where act_date > '2016-01-01' and act_date < '2016-12-31' and marketing='email') and state='california';")
    sqls.append("select prod_name from finance_products where prod_id=(select prod_id from transactions group by prod_id order by count(*) desc limit 1);")
    sqls.append("select f.family_id, f.last_name from families f inner join transactions t on f.family_id = t.family_id inner join finance_products p on p.prod_id = t.prod_id where prod_name='Small Business Insurance' and state='texas' and activity='purchased';")
    sqls.append("select state,count(*) from families where family_id in (select family_id from transactions where act_date > '2016-01-01' and act_date < '2016-12-31' and activity='renewed') group by state;")
    sqls.append("select count(*) from transactions where marketing='search' and prod_id=(select prod_id from finance_products where prod_name='Auto Insurance');")

    sqls.append("select count(*) as volume,prod_name from families f inner join transactions t on f.family_id = t.family_id inner join finance_products p on p.prod_id = t.prod_id group by prod_name;")
    sqls.append("select count(*),prod_name,DATE_FORMAT(act_date, \"%y-%m\") as month_date from families f inner join transactions t on f.family_id = t.family_id inner join finance_products p on p.prod_id = t.prod_id where prod_name='Auto Insurance' or prod_name='Rental Insurance' group by month_date,prod_name;")
    sqls.append("select count(*) as volume,l.state,l.lat,l.longitude from families f inner join transactions t on f.family_id = t.family_id inner join finance_products p on p.prod_id = t.prod_id inner join lat_long l on f.state=l.state where marketing='email' group by state;")

    assert(len(sentences)==len(sqls))
    for i in range(len(sentences)):
        f = stem_filter_check(sentences[i])
        mapper[f] = (sqls[i],'q'+str(i+1)+'_query',sentences[i])
       # map(result of stem-filter-check) = (sql-transalation , q3_query , cleaned english sentence) 

    mapper['Show me the number of male and female employees']=('select gender,count(*) from employees group by gender;','gender_query')
    mapper['Show the number of employees in each department']=('select dept_no,count(*) from dept_emp group by dept_no;','')
    mapper['What is the number of employees in each title']=('select title,count(*) from titles group by title;','title_query')
    mapper['What are the last names of the employees whose salary is more than 150000']=('select last_name from employees where emp_no in (select emp_no from salaries where salary > 150000);','')
    return mapper

def stem_filter_check(ip_string):
    f = re.findall(r"[\w]+",ip_string.lower())
    #f = " ".join(f)
    corrected_words = [sc.correction(i) for i in f]

    stop_words = set(['me','of','a','in','to','are','is','for','am','on']) 
    #stop_words = set(stopwords.words('english'))
    stop_words = stop_words - set(['which','how','where','what','and','or'])
    filtered_words = [i for i in corrected_words if i not in stop_words]

    stemmer = SnowballStemmer("english")
    #stemmed_words = filtered_words 
    stemmed_words = [stemmer.stem(i) for i in filtered_words]

    return "".join(stemmed_words)


def translate(ip_string):
    processed_str = stem_filter_check(ip_string)
    mapper = get_mappings()
    if mapper.has_key(processed_str):
        return mapper[processed_str][0].decode('unicode-escape')
    else:
        return 'NA'

<<<<<<< HEAD
=======

#
# Run a parameterized query synchronously and return the result
# DISCLAIMER: Temporary solution to support parameters in queries. Should be
#             removed once we refactor the query results API endpoints and handling
#             on the client side. Please don't reuse in other API handlers.
#
def run_query_sync(data_source, parameter_values, query_text, max_age=0):
    query_parameters = set(collect_query_parameters(query_text))
    missing_params = set(query_parameters) - set(parameter_values.keys())
    if missing_params:
        raise Exception('Missing parameter value for: {}'.format(", ".join(missing_params)))

    if query_parameters:
        query_text = pystache.render(query_text, parameter_values)

    if max_age <= 0:
        query_result = None
    else:
        query_result = models.QueryResult.get_latest(data_source, query_text, max_age)

    query_hash = gen_query_hash(query_text)

    if query_result:
        logging.info("Returning cached result for query %s" % query_hash)
        return query_result

    try:
        started_at = time.time()
        data, error = data_source.query_runner.run_query(query_text, current_user)

        if error:
            logging.info('got bak error')
            logging.info(error)
            return None

        run_time = time.time() - started_at
        query_result, updated_query_ids = models.QueryResult.store_result(data_source.org, data_source,
                                                                              query_hash, query_text, data,
                                                                              run_time, utils.utcnow())

        models.db.session.commit()
        return query_result
    except Exception, e:
        if max_age > 0:
            abort(404, message="Unable to get result from the database, and no cached query result found.")
        else:
            abort(503, message="Unable to get result from the database.")
        return None
>>>>>>> 001ce29eba1fcd690a3c4c2691b90b998eb5628a

def run_query(data_source, parameter_values, query_text, query_id, max_age=0):
    # adds a job if max_age=0 -> /job and /event calls 
    # how is status=3 prompting /query_results/2 call ?
    # anyway, query_result/2 call - model.py - gets final result through db.sessions
    # how is celery job connected to db.session object ??

    #return error_response('New Query text variable is <{}>, param values is <{}>, query id is <{}>, max age is <{}>'.format(query_text,parameter_values,query_id, max_age))
    original_text = query_text
    query_text = translate(query_text)
    if query_text == 'NA':
        query_text = original_text

    #return error_response('New Query text variable is <{}>, param values is <{}>, query id is <{}>, max age is <{}>'.format(query_text,parameter_values,query_id, max_age))
    query_parameters = set(collect_query_parameters(query_text))
    missing_params = set(query_parameters) - set(parameter_values.keys())
    if missing_params:
        return error_response('Missing parameter value for: {}'.format(", ".join(missing_params)))

    if data_source.paused:
        if data_source.pause_reason:
            message = '{} is paused ({}). Please try later.'.format(data_source.name, data_source.pause_reason)
        else:
            message = '{} is paused. Please try later.'.format(data_source.name)

        return error_response(message)

    if query_parameters:
        query_text = pystache.render(query_text, parameter_values)

    if max_age == 0:
        query_result = None
    else:
        query_result = models.QueryResult.get_latest(data_source, query_text, max_age)

    if query_result:
        return {'query_result': query_result.to_dict()}
    else:
        job = enqueue_query(query_text, data_source, current_user.id, metadata={"Username": current_user.email, "Query ID": query_id})
        return {'job': job.to_dict()}


# execute directly query
class QueryResultListResource(BaseResource):
    @require_permission('execute_query')
    def post(self):
        """
        Execute a query (or retrieve recent results).

        :qparam string query: The query text to execute
        :qparam number query_id: The query object to update with the result (optional)
        :qparam number max_age: If query results less than `max_age` seconds old are available, return them, otherwise execute the query; if omitted, always execute
        :qparam number data_source_id: ID of data source to query
        """
        params = request.get_json(force=True)
        parameter_values = collect_parameters_from_request(request.args)

        query = params['query']
        max_age = int(params.get('max_age', -1))
        query_id = params.get('query_id', 'adhoc')

        data_source = models.DataSource.get_by_id_and_org(params.get('data_source_id'), self.current_org)

        if not has_access(data_source.groups, self.current_user, not_view_only):
            return {'job': {'status': 4, 'error': 'You do not have permission to run queries with this data source.'}}, 403

        self.record_event({
            'action': 'execute_query',
            'timestamp': int(time.time()),
            'object_id': data_source.id,
            'object_type': 'data_source',
            'query': query
        })

        return run_query(data_source, parameter_values, query, query_id, max_age)


ONE_YEAR = 60 * 60 * 24 * 365.25


class QueryResultResource(BaseResource):
    @staticmethod
    def add_cors_headers(headers):
        if 'Origin' in request.headers:
            origin = request.headers['Origin']

            if set(['*', origin]) & settings.ACCESS_CONTROL_ALLOW_ORIGIN:
                headers['Access-Control-Allow-Origin'] = origin
                headers['Access-Control-Allow-Credentials'] = str(settings.ACCESS_CONTROL_ALLOW_CREDENTIALS).lower()

    @require_permission('view_query')
    def options(self, query_id=None, query_result_id=None, filetype='json'):
        headers = {}
        self.add_cors_headers(headers)

        if settings.ACCESS_CONTROL_REQUEST_METHOD:
            headers['Access-Control-Request-Method'] = settings.ACCESS_CONTROL_REQUEST_METHOD

        if settings.ACCESS_CONTROL_ALLOW_HEADERS:
            headers['Access-Control-Allow-Headers'] = settings.ACCESS_CONTROL_ALLOW_HEADERS

        return make_response("", 200, headers)

    @require_permission('view_query')
    def get(self, query_id=None, query_result_id=None, filetype='json'):
        """
        Retrieve query results.

        :param number query_id: The ID of the query whose results should be fetched
        :param number query_result_id: the ID of the query result to fetch
        :param string filetype: Format to return. One of 'json', 'xlsx', or 'csv'. Defaults to 'json'.

        :<json number id: Query result ID
        :<json string query: Query that produced this result
        :<json string query_hash: Hash code for query text
        :<json object data: Query output
        :<json number data_source_id: ID of data source that produced this result
        :<json number runtime: Length of execution time in seconds
        :<json string retrieved_at: Query retrieval date/time, in ISO format
        """
        # TODO:
        # This method handles two cases: retrieving result by id & retrieving result by query id.
        # They need to be split, as they have different logic (for example, retrieving by query id
        # should check for query parameters and shouldn't cache the result).

        should_cache = query_result_id is not None

        parameter_values = collect_parameters_from_request(request.args)
        max_age = int(request.args.get('maxAge', 0))

        query_result = None

        if query_result_id:
            query_result = get_object_or_404(models.QueryResult.get_by_id_and_org, query_result_id, self.current_org)
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> 001ce29eba1fcd690a3c4c2691b90b998eb5628a
            # this is the table only result - a new one every time execute button is clicked
            # don't update this variable - can't call another func here cause we don't have query_id to update (maybe adhoc)
        else:
            query_result = None
=======
        elif query_id is not None:
            query = get_object_or_404(models.Query.get_by_id_and_org, query_id, self.current_org)

            if query is not None:
                if settings.ALLOW_PARAMETERS_IN_EMBEDS and parameter_values:
                    query_result = run_query_sync(query.data_source, parameter_values, query.to_dict()['query'], max_age=max_age)
                elif query.latest_query_data_id is not None:
                    query_result = get_object_or_404(models.QueryResult.get_by_id_and_org, query.latest_query_data_id, self.current_org)
>>>>>>> 5b54a777d91e18398f68fcae4bdc669f438faec0

        if query_result:
            require_access(query_result.data_source.groups, self.current_user, view_only)

            if isinstance(self.current_user, models.ApiUser):
                event = {
                    'user_id': None,
                    'org_id': self.current_org.id,
                    'action': 'api_get',
                    'timestamp': int(time.time()),
                    'api_key': self.current_user.name,
                    'file_type': filetype,
                    'user_agent': request.user_agent.string,
                    'ip': request.remote_addr
                }

                if query_id:
                    event['object_type'] = 'query'
                    event['object_id'] = query_id
                else:
                    event['object_type'] = 'query_result'
                    event['object_id'] = query_result_id

                record_event.delay(event)

            query_result_dict = query_result.to_dict()

            # TODO saving again even saved queries - Solved
            # but correct way is through frontend js ... sepearate endpoint, here same string saved again as new query won't auto visualise
            # another bug ? if sql directly typed again - then auto visualize wont happen
            
            mapper = get_mappings()
            file_name = None
            saved_query_id = None
            for k in mapper:
                if (mapper[k][0] == query_result_dict['query']):
                    file_name = mapper[k][1]
                    query_text = mapper[k][2]
            #query_name = None
            if file_name:
                if (not query_result.is_same_query(query_text, query_result.data_source)):
                    # 1. save the query 2. get predefined visual json 3. add json to query object visualizations
                    visualization_resource = VisualizationListResource()
<<<<<<< HEAD
	            try:
                        saved_query_id = visualization_resource.save_and_add_visual(query_result_dict, file_name, query_text)
                    except Exception as e:
                        abort(500,e.message)                    # TODO try catch
                    #saved_query_id = visualization_resource.save_and_add_visual(query_result_dict, file_name, query_text)
=======
                    # TODO try catch
                    try:
                        saved_query_id = visualization_resource.save_and_add_visual(query_result_dict, file_name, query_text)
                    except Exception as e:
                        abort(500,e.message)
>>>>>>> 001ce29eba1fcd690a3c4c2691b90b998eb5628a

            if saved_query_id:
                query_result_dict['query_id'] = saved_query_id


            if filetype == 'json':
                response = self.make_json_response(query_result_dict)
            elif filetype == 'xlsx':
                response = self.make_excel_response(query_result)
            else:
                response = self.make_csv_response(query_result)

            if len(settings.ACCESS_CONTROL_ALLOW_ORIGIN) > 0:
                self.add_cors_headers(response.headers)

            if should_cache:
                response.headers.add_header('Cache-Control', 'max-age=%d' % ONE_YEAR)

            return response

        else:
            abort(404, message='No cached result found for this query.')


    def make_json_response(self, query_result_dict):
        data = json.dumps({'query_result': query_result_dict}, cls=utils.JSONEncoder)
        headers = {'Content-Type': "application/json"}
        return make_response(data, 200, headers)

    @staticmethod
    def make_csv_response(query_result):
        headers = {'Content-Type': "text/csv; charset=UTF-8"}
        return make_response(query_result.make_csv_content(), 200, headers)

    @staticmethod
    def make_excel_response(query_result):
        headers = {'Content-Type': "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
        return make_response(query_result.make_excel_content(), 200, headers)


class JobResource(BaseResource):
    def get(self, job_id):
        """
        Retrieve info about a running query job.
        """
        job = QueryTask(job_id=job_id)
        return {'job': job.to_dict()}

    def delete(self, job_id):
        """
        Cancel a query job in progress.
        """
        job = QueryTask(job_id=job_id)
        job.cancel()
