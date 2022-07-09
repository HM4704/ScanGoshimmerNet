import NodeInfo
import wx
import requests
from threading import Thread
import json
from pubsub import pub
from multiprocessing import Queue


class ScanThread(Thread):

    running = False
    firstIp = ""
    def __init__(self, firstIp):
        Thread.__init__(self)
        self._status = ""
        self._observers = []
        self.ni = NodeInfo.NodeInfo()
        self.running = True
        self.queue = Queue()
        self.firstIp = firstIp
        self.start()  # start the thread

    def run(self):
        self.getKnownNodes(self.firstIp)
        while (self.running):
            # Wait for next message
            self.status = "  idle"
            message = self.queue.get()
            print("got message " + message)
            if (len(message) > 0):
                self.status = "  querying " + message
                self.ni = self.get(message)
                wx.CallAfter(self.postData, 0)

    def stop(self):
        self.status = "  stopping"
        self.running = False

    def postData(self, amt):
        pub.sendMessage("node_listener", message=self.ni)

    def get(self, ip):
        ni = NodeInfo.NodeInfo()
        ni.ip = ip
        try:
            self.r = requests.get('http://' + ip + ':8080/info', timeout=2000)
        except:
            return ni
        if self.r.ok == True:
            ni.enabledAPI = True
            info = json.loads(self.r.text)
            tt = info['tangleTime']
            ni.synced = tt['synced']
            ni.shortId = info['identityIDShort']
            mana = info['mana']
            ni.accessMana = mana['access']
        return ni

    def getKnownNodes(self, ip):
        try:
            self.r = requests.get('http://' + ip + ':8080/autopeering/neighbors?known=1', timeout=2000)
            neighbors = json.loads(self.r.text)
        except:
            return
        known = neighbors['known']
        count = len(known)
        act = 1
        for entry in known:
            services = entry['services']
            ip = services[0]['address']
            if ':' in ip:
                ip = ip.split(':')[0]
            self.status = "  querying " + ip + "  :  " + str(act) + " / " + str(count)
            self.ni = self.get(ip)
            self.ni.shortId = entry['id']
            wx.CallAfter(self.postData, 0)
            act = act + 1
            if self.running == False: break

        return

    def putMessage(self, message):
        self.queue.put(message)

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value
        for callback in self._observers:
            callback(self._status)

    def bind_to(self, callback):
        self._observers.append(callback)
