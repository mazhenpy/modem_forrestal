import json

from handlers import BaseHandler


class AdminOperateHandler(BaseHandler):
    def post(self):
        body = self.request.body.decode()
        args = json.loads(body)

        self.finish(json.dumps(args))