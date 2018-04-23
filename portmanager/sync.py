# encoding: utf8
import logging
import tornado.gen
from portmanager.tor_para import SSHClientManager

request_log = logging.getLogger("config")

SUPER_CONF = '''
cat << EOF | sudo tee /etc/supervisor/conf.d/port_{port_id}.conf
[program:port_{port_id}]
command={ssh_base}/env/bin/python3 modem_port.py --config=config_{port_id}.yaml --log=logging_{port_id}.yaml
directory={ssh_base}/modem_port
user={ssh_user}
redirect_stderr=false
stdout_logfile={ssh_base}/modem_port/logs/port-{port_id}-stdout.log
stderr_logfile={ssh_base}/modem_port/logs/port-{port_id}-stderr.log
EOF
'''


class PortManager:
    def __init__(self, application):
        self.application = application
        self._master = None
        self.ssh_manager = SSHClientManager()

    @property
    def master(self):
        if self._master is None:
            self._master = self.application.redis_driver.master
        return self._master

    @tornado.gen.coroutine
    def sync_user(self, new_cfg):
        """
        pm:user:800001
          account -> test
          password -> testpassword
          port -> 800001
        pm:port:800001
          instance ->
          path
          task_name ->
        pm:instance:jinyue
          host
          port
          user
          password
          count
          basepath
        """
        request_log.info('SYNC USER START')

        master = self.master

        up_user_list = new_cfg.get('up_user')
        fuel_acct_map = new_cfg.get('fuel_account')

        if fuel_acct_map is None:
            request_log.warn('FUEL ACCOUNT NOT CONFIG')
            return

        try:
            for user_id in up_user_list:
                request_log.info('PROCESSING %s', user_id)

                if user_id not in fuel_acct_map:
                    request_log.error('USER %s WITHOUT ACCOUNT', user_id)
                    continue

                acct = fuel_acct_map[user_id]
                # request_log.debug('USER %s -> FUEL %s', user_id, account)
                k = 'pm:user:%s' % user_id

                if not master.exists(k):
                    request_log.info('NEW USER %s', user_id)
                    yield self.new_user(user_id, up_user_list[user_id], acct)
                else:
                    old_account, old_password = master.hmget(k, ['account', 'password'])

                    if acct['account'] != old_account or acct['password'] != old_password:
                        request_log.info('UPDATE USER %s', user_id)
                        yield self.update_user(user_id, up_user_list[user_id], acct)
                        master.hmset(k, {'account': acct['account'], 'password': acct['password']})
        except:
            request_log.exception("SYNC FAIL")

        request_log.info('SYNC USER END')

    @tornado.gen.coroutine
    def new_user(self, user_id, up_user_obj, acct):
        # found instance
        master = self.master

        port_id = user_id
        port_k = 'pm:port:' + port_id
        if master.exists(port_k):
            request_log.error('PORT EXIST %s', port_k)
            return

        instance_ids = master.keys('pm:instance:*')
        ins_k = instance_ids[0]
        ssh_host, ssh_port, ssh_user, ssh_password, ssh_base = master.hmget(
                ins_k, ['host', 'port', 'user', 'password', 'basepath'])

        client = self.ssh_manager.get_client(ssh_host, ssh_user, int(ssh_port), password=ssh_password)

        port_path = ssh_base + '/modem_port'

        run_port = 11110 + int(port_id[-1])  # work around

        # create config_user from config
        # create logging_user from logging
        r = yield client.exec_command(
                'cp %s/config.yaml %s/config_%s.yaml' % (port_path, port_path, port_id))
        request_log.debug('RESULT {%s}', r)
        r = yield client.exec_command(
                'cp %s/logging.yaml %s/logging_%s.yaml' % (port_path, port_path, port_id))
        request_log.debug('RESULT {%s}', r)

        # re-config
        r = yield client.exec_command(
                'sed -i "s/^  user:.*/  user: \'%s\'/" %s/config_%s.yaml' % (acct['account'], port_path, port_id))
        request_log.debug('RESULT {%s}', r)
        r = yield client.exec_command(
                'sed -i "s/^  pass:.*/  pass: \'%s\'/" %s/config_%s.yaml' % (acct['password'], port_path, port_id))
        request_log.debug('RESULT {%s}', r)

        r = yield client.exec_command(
                'sed -i "s/^  site:.*/  site: \'%s\'/" %s/config_%s.yaml' % (user_id, port_path, port_id))
        request_log.debug('RESULT {%s}', r)
        r = yield client.exec_command(
                'sed -i "s/^  aes_pass:.*/  aes_pass: \'%s\'/" %s/config_%s.yaml' % (
                up_user_obj['aes_pass'], port_path, port_id))
        request_log.debug('RESULT {%s}', r)
        r = yield client.exec_command(
                'sed -i "s/^  aes_iv:.*/  aes_iv: \'%s\'/" %s/config_%s.yaml' % (
                    up_user_obj['aes_iv'], port_path, port_id))
        request_log.debug('RESULT {%s}', r)
        r = yield client.exec_command(
                'sed -i "s/^  port:.*/  port: %d/" %s/config_%s.yaml' % (run_port, port_path, port_id))
        request_log.debug('RESULT {%s}', r)

        r = yield client.exec_command(
                'sed -i "s/filename:.*/filename: \'logs\/request_%s.log\'/" %s/logging_%s.yaml' % (
                    port_id, port_path, port_id))
        request_log.debug('RESULT {%s}', r)

        # config supervisor
        command = SUPER_CONF.format(port_id=port_id, ssh_base=ssh_base, ssh_user=ssh_user)
        request_log.debug('TO EXECUTE %s', command)
        r = yield client.exec_command(command)
        logging.debug('{RESULT: %s}', r)

        r = yield client.exec_command("sudo supervisorctl update")
        logging.debug('{RESULT: %s}', r)

        # config redis
        master.hmset('pm:user:' + user_id, {
            'account': acct['account'],
            'password': acct['password'],
            'port': port_id
        })

        master.hmset('pm:port:' + port_id, {
            'instance': ins_k.split(':')[-1],
            'path': port_path,
            'task_name': 'port_' + port_id
        })

    @tornado.gen.coroutine
    def update_user(self, user_id, up_user, acct):
        request_log.debug('%s %s', up_user, acct)

        # found instance
        master = self.master
        k = 'pm:user:' + user_id
        port_id = master.hget(k, 'port')
        if port_id is None:
            request_log.error('CANNOT GET PORT FOR USER %s', user_id)
            return

        # found port
        k = 'pm:port:' + port_id
        instance_id, path, task_name = master.hmget(k, ['instance', 'path', 'task_name'])

        k = 'pm:instance:' + instance_id
        ssh_host, ssh_port, ssh_user, ssh_password = master.hmget(k, ['host', 'port', 'user', 'password'])

        client = self.ssh_manager.get_client(ssh_host, ssh_user, int(ssh_port), password=ssh_password)

        r = yield client.exec_command('cp %s/config_%s.yaml %s/config_%s.bak' % (path, user_id, path, user_id))
        request_log.debug('RESULT {%s}', r)
        r = yield client.exec_command(
            'sed -i "s/^  user:.*/  user: \'%s\'/" %s/config_%s.yaml' % (acct['account'], path, user_id))
        request_log.debug('RESULT {%s}', r)
        r = yield client.exec_command(
            'sed -i "s/^  pass:.*/  pass: \'%s\'/" %s/config_%s.yaml' % (acct['password'], path, user_id))
        request_log.debug('RESULT {%s}', r)

        r = yield client.exec_command('sudo supervisorctl restart %s' % task_name)
        request_log.debug('RESULT {%s}', r)
        # stop node
        # edit config
        # start node
