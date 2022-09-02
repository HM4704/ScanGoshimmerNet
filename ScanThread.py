import NodeInfo
import wx
import requests
from threading import Thread
import json
from pubsub import pub
from multiprocessing import Queue


class ScanThread(Thread):
    idleStatus = " idle"
    running = False
    firstIp = ""
    inaccNodes = {}

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
        self.status = self.queryKnownNodes(self.firstIp)
        while (self.running):
            # Wait for next message
            message = self.queue.get()
            print("got message " + message)
            if (len(message) > 0):
                if message[0] == '*':
                    ip = message[1:]
                    self.status = self.queryKnownNodes(ip)
                elif message[0] == 'c':
                    self.inaccNodes.clear()
                else:
                    self.status = "  querying " + message
                    self.ni,self.status = self.getNodeInfo(message)
                    wx.CallAfter(self.postData, 0)

    def stop(self):
        self.status = "  stopping"
        self.running = False
        self.putMessage("")

    def postData(self, amt):
        pub.sendMessage("node_listener", message=self.ni)

    def queryKnownNodes(self, ip):
        nodes = []
        s = self.getKnownNodes(ip, nodes)
        if (len(s) == 0):
            s = self.idleStatus
            self.queryNodes(nodes)
        return s

    def getNodeInfo(self, ip):
        ni = NodeInfo.NodeInfo()
        ni.ip = ip
        if ip in self.inaccNodes:
            return (ni, self.inaccNodes[ip])            
        try:
            self.r = requests.get('http://' + ip + ':8080/info', timeout=2)
        except Exception as inst:
            err = "error " + str(type(inst)) + " while querying " + str(ip)
            self.inaccNodes[ip] = err
            return (ni, err)
        if self.r.ok == True:
            ni.enabledAPI = True
            info = json.loads(self.r.text)
            tt = info['tangleTime']
            ni.synced = tt['synced']
            ni.att = tt['ATT']
            ni.shortId = info['identityIDShort']
            mana = info['mana']
            ni.accessMana = mana['access']
            ni.version = info['version']
        return (ni, self.idleStatus)

    def getKnownNodes(self, ip, nodes):
        try:
            self.r = requests.get('http://' + ip + ':8080/autopeering/neighbors?known=1', timeout=3)
            neighbors = json.loads(self.r.text)
        except Exception as inst:
            return "error " + str(type(inst)) + " while querying " + str(ip)
        n = neighbors['known']
        for entry in n:
            nodes.append(entry)
        return ""

                
    def queryNodes(self, nodes):
        count = len(nodes)
        act = 1
        for entry in nodes:
            services = entry['services']
            ip = services[0]['address']
            if ':' in ip:
                ip = ip.split(':')[0]
            self.status = "  querying " + ip + "  :  " + str(act) + " / " + str(count)
            self.ni,err = self.getNodeInfo(ip)
            self.ni.shortId = entry['id']
            wx.CallAfter(self.postData, 0)
            act = act + 1
            if self.running == False: break

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
        
    def cmdQueryAll(self, ip, clear=False):
        if clear == True:
            self.putMessage('c')            
        self.putMessage('*' + ip)
        
    def cmdQuery(self, ip):
        self.putMessage(ip)

