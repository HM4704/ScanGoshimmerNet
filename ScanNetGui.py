import wx
import argparse
import ScanThread
from pubsub import pub
from datetime import datetime
import wx.lib.mixins.listctrl


class SortedListCtrl(wx.ListCtrl, wx.lib.mixins.listctrl.ColumnSorterMixin):

    def __init__(self, parent, data, colCount):

        wx.ListCtrl.__init__(self, parent, wx.ID_ANY, style=wx.LC_REPORT)
        wx.lib.mixins.listctrl.ColumnSorterMixin.__init__(self, colCount)
        self.itemDataMap = data

    def GetListCtrl(self):
        return self


class GridFrame(wx.Frame):

    nodes = {}

    def __init__(self, parent, node):
        wx.Frame.__init__(self, parent, title="Goshimmer nodes", size=(1100,800))

        panel = wx.Panel(self)
        box = wx.BoxSizer(wx.HORIZONTAL)

        self.list = SortedListCtrl(panel, data=self.nodes, colCount=7)
        self.list.InsertColumn(0, 'IP', wx.LIST_FORMAT_CENTER, 150)
        self.list.InsertColumn(1, 'ID', wx.LIST_FORMAT_CENTER, 150)
        self.list.InsertColumn(2, 'synced', wx.LIST_FORMAT_CENTER, 150)
        self.list.InsertColumn(3, 'API(Port 8080)', wx.LIST_FORMAT_CENTER, 150)
        self.list.InsertColumn(4, 'Indexer', wx.LIST_FORMAT_RIGHT, 150)
        self.list.InsertColumn(5, 'ATT', wx.LIST_FORMAT_RIGHT, 200)
        self.list.InsertColumn(6, 'Version', wx.LIST_FORMAT_RIGHT, 100)

        box.Add(self.list, 1, wx.EXPAND)
        panel.SetSizer(box)
        panel.Fit()

        self.statusBar = self.CreateStatusBar(style = wx.BORDER_NONE|wx.RIGHT)
        self.statusBar.SetStatusText("Status Bar")

        self.Bind(wx.EVT_CLOSE, self.OnClose)

        pub.subscribe(self.update, "node_listener")
        self.thread = ScanThread.ScanThread(node)
        self.thread.bind_to(self.updateStatus)
        self.thread.cmdQuery("127.0.0.1")
        #self.thread.cmdQuery("localhost:8051")

        self.popupmenu = wx.Menu()
        item = self.popupmenu.Append(-1, "copy IP")
        self.Bind(wx.EVT_MENU, self.OnPopupItemCopyIp, item)
        item = self.popupmenu.Append(-1, "query again")
        self.Bind(wx.EVT_MENU, self.OnPopupItemQuery, item)
        self.mnItemQueryAll = self.popupmenu.Append(-1, "query all")
        self.Bind(wx.EVT_MENU, self.OnPopupQueryAll, self.mnItemQueryAll)
        self.mnItemQueryAll = self.popupmenu.Append(-1, "refresh all")
        self.Bind(wx.EVT_MENU, self.RefreshAllNodes, self.mnItemQueryAll)

        self.list.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        
        self.Show(True)

    def on_button_click(self, event):
        wx.MessageBox("Button clicked!")
        
    def updateItem(self, nodeInfo):
        for idx in range(0, self.list.GetItemCount()):
            ip = self.list.GetItemText(idx, 0)
            if ip == nodeInfo.ip:
                key = self.list.GetItemData(idx)
                self.nodes[key] = (nodeInfo.ip, nodeInfo.shortId,nodeInfo.synced,nodeInfo.enabledAPI,nodeInfo.indexer,nodeInfo.att,nodeInfo.version)
                self.updateLine(idx, nodeInfo)
                return True
        return False

    def update(self, message, arg2=None):
        if not self.updateItem(message):
            key = len(self.nodes)
            self.nodes[key] = (message.ip,message.shortId,message.synced,message.enabledAPI,message.indexer,message.att,message.version)
            index = self.list.InsertItem(0, message.ip)

            self.updateLine(index, message)
            self.list.SetItemData(index, key)
            # do deep search
            if message.enabledAPI == True:
                self.thread.cmdQueryAll(message.ip)

    def updateLine(self, index, nodeInfo):
            self.list.SetItem(index, 3, str(nodeInfo.enabledAPI))
            self.list.SetItem(index, 1, nodeInfo.shortId)
            if nodeInfo.enabledAPI:
                self.list.SetItem(index, 2, str(nodeInfo.synced))
                self.list.SetItem(index, 4, str(nodeInfo.indexer))
                att = str(datetime.fromtimestamp(nodeInfo.att/1000000000))
                att = att.split('.')[0]  # throw away decimals
                self.list.SetItem(index, 5, att)
                self.list.SetItem(index, 6, nodeInfo.version)
            else:
                self.list.SetItem(index, 2, "?")
                self.list.SetItem(index, 4, "?")
                self.list.SetItem(index, 5, "?")
                self.list.SetItem(index, 6, "?")

    def updateStatus(self, status):
        wx.CallAfter(self.OnStatus, status)

    def OnStatus(self, event):
        self.statusBar.SetStatusText(event)

    def GetSelectedIp(self):
        item = self.list.GetFirstSelected()
        if item != -1:
            ip = self.list.GetItemText(item, )
            return ip
        return ""

    def GetSelectedID(self):
        item = self.list.GetFirstSelected()
        if item != -1:
            id = self.list.GetItemText(item, 1)
            return id
        return ""

    def HasSelectedApi(self):
        item = self.list.GetFirstSelected()
        if item != -1:
            api = self.list.GetItemText(item, col=3)
            return api == 'True'
        return False

    def OnPopupItemQuery(self, event):
        item = self.popupmenu.FindItemById(event.GetId())
        ip = self.GetSelectedIp()
        if len(ip) > 0:
            id = self.GetSelectedID()
            self.thread.cmdQuery(ip + ':' + id)
        else:
            wx.MessageBox("Select a line in the list")

    def OnPopupItemCopyIp(self, event):
        item = self.popupmenu.FindItemById(event.GetId())
        ip = self.GetSelectedIp()
        if len(ip) == 0:
            wx.MessageBox("Select a line in the list")
            return
        clipdata = wx.TextDataObject()
        clipdata.SetText(ip)
        wx.TheClipboard.Open()
        wx.TheClipboard.SetData(clipdata)
        wx.TheClipboard.Close()

    def OnPopupQueryAll(self, event):
        item = self.popupmenu.FindItemById(event.GetId())
        ip = self.GetSelectedIp()
        if len(ip) > 0:
            self.list.DeleteAllItems()
            self.nodes.clear()
            self.thread.cmdQueryAll(ip, clear=True)
        else:
            wx.MessageBox("Select a line in the list")

    def RefreshAllNodes(self, event):
        item_count = self.list.GetItemCount()
        for item_index in range(item_count):
            ip = self.list.GetItemText(item_index, 0)
            id = self.list.GetItemText(item_index, 1)
            self.thread.cmdQuery(ip + ":" +  id)
            
            
    def OnRightDown(self, event):
        if self.list.GetFirstSelected() != -1:
            pos = event.GetPosition()
            #pos = self.list.ScreenToClient(pos)
            self.mnItemQueryAll.Enable(self.HasSelectedApi())
            self.PopupMenu(self.popupmenu, pos)


    def OnClose(self, event):
        self.thread.stop()
        self.Destroy()  # you may also do:  event.Skip()
                        # since the default event handler does call Destroy(), too

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scan goshimmer network')
    parser.add_argument('-node', type=str, default="192.168.178.33",
                        help='bootstrap node to start the scan')

    args = parser.parse_args()
    print(args.node)

    app = wx.App(0)
    frame = GridFrame(None, node=args.node)
    app.MainLoop()