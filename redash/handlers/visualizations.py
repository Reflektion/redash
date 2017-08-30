import json
#import random
from flask import request

from redash import models
from redash.permissions import require_permission, require_admin_or_owner
from redash.handlers.base import BaseResource, get_object_or_404

import redash.handlers.queries

class VisualizationListResource(BaseResource):
    @require_permission('edit_query')
    def post(self):
        kwargs = request.get_json(force=True)

        d = self.add_visual(kwargs)        
        return d

    # modified to also add a visualization from the backend along with the front end API call
    def add_visual(self, kwargs):
        query = get_object_or_404(models.Query.get_by_id_and_org, kwargs.pop('query_id'), self.current_org)
        require_admin_or_owner(query.user_id)

        kwargs['options'] = json.dumps(kwargs['options'])
        kwargs['query_rel'] = query

        vis = models.Visualization(**kwargs)
        models.db.session.add(vis)
        models.db.session.commit()
        d = vis.to_dict(with_query=False)
        return d

    def save_and_add_visual(self,query_result_dict,file_name,query_text):
        # 1. save the query

        payload = {}
        #hash1 = random.getrandbits(64)
        #hash1_string = '%04x_' % hash1
        payload['name'] = 'My New Query'#'auto_' + hash1_string + file_name
        payload['data_source_id'] = query_result_dict['data_source_id']
        payload['query'] = query_text
        payload['schedule'] = query_result_dict.get('schedule',None)
        payload['latest_query_data_id'] = query_result_dict['id']

        # no need to handle parameters - already processed in run_query()
        payload['options'] = {}
        payload['options']['parameters'] = []

        query_resource = redash.handlers.queries.QueryListResource()
        saved_query = query_resource.add_query(payload)
        saved_query_id = saved_query.id

        if file_name in ['q6_query','q7_query']:
            return saved_query_id

        # 2. retreive predfined json
        with open('/app/redash/handlers/visual_files/'+str(file_name)) as vis_file:
            vis_payload = json.load(vis_file)

        # 3. add json to the query we just saved        
        vis_payload['query_id'] = saved_query_id
        self.add_visual(vis_payload)
        return saved_query_id


class VisualizationResource(BaseResource):
    @require_permission('edit_query')
    def post(self, visualization_id):
        vis = get_object_or_404(models.Visualization.get_by_id_and_org, visualization_id, self.current_org)
        require_admin_or_owner(vis.query_rel.user_id)

        kwargs = request.get_json(force=True)
        if 'options' in kwargs:
            kwargs['options'] = json.dumps(kwargs['options'])

        kwargs.pop('id', None)
        kwargs.pop('query_id', None)

        self.update_model(vis, kwargs)
        d = vis.to_dict(with_query=False)
        models.db.session.commit()
        return d

    @require_permission('edit_query')
    def delete(self, visualization_id):
        vis = get_object_or_404(models.Visualization.get_by_id_and_org, visualization_id, self.current_org)
        require_admin_or_owner(vis.query_rel.user_id)
        models.db.session.delete(vis)
        models.db.session.commit()
