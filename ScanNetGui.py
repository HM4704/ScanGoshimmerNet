import wx
import argparse
import ScanThread
from pubsub import pub
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
        wx.Frame.__init__(self, parent, title="Goshimmer nodes", size=(900,800))

        panel = wx.Panel(self)
        box = wx.BoxSizer(wx.HORIZONTAL)

        self.list = SortedListCtrl(panel, data=self.nodes, colCount=5)
        self.list.InsertColumn(0, 'IP', wx.LIST_FORMAT_CENTER, 150)
        self.list.InsertColumn(1, 'ID', wx.LIST_FORMAT_CENTER, 150)
        self.list.InsertColumn(2, 'synced', wx.LIST_FORMAT_CENTER, 150)
        self.list.InsertColumn(3, 'API(Port 8080)', wx.LIST_FORMAT_CENTER, 150)
        self.list.InsertColumn(4, 'aMana', wx.LIST_FORMAT_RIGHT, 150)

        box.Add(self.list, 1, wx.EXPAND)
        panel.SetSizer(box)
        panel.Fit()

        self.statusBar = self.CreateStatusBar(style = wx.BORDER_NONE|wx.RIGHT)
        self.statusBar.SetStatusText("Status Bar")

        self.Bind(wx.EVT_CLOSE, self.OnClose)

        pub.subscribe(self.update, "node_listener")
        self.thread = ScanThread.ScanThread(node)
        self.thread.bind_to(self.updateStatus)

        self.popupmenu = wx.Menu()
        item = self.popupmenu.Append(-1, "copy IP")
        self.Bind(wx.EVT_MENU, self.OnPopupItemCopyIp, item)
        item = self.popupmenu.Append(-1, "query again")
        self.Bind(wx.EVT_MENU, self.OnPopupItemQuery, item)

        self.list.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)

        self.Show(True)


    def update(self, message, arg2=None):
        key = len(self.nodes)
        self.nodes[key] = (message.ip,message.shortId,message.synced,message.enabledAPI,message.accessMana)
        index = self.list.InsertItem(0, message.ip)
        self.list.SetItem(index, 3, str(message.enabledAPI))
        self.list.SetItem(index, 1, message.shortId)
        if message.enabledAPI:
            self.list.SetItem(index, 2, str(message.synced))
            self.list.SetItem(index, 4, str(message.accessMana))
        else:
            self.list.SetItem(index, 2, "?")
            self.list.SetItem(index, 4, "?")
        self.list.SetItemData(index, key)

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

    def OnPopupItemQuery(self, event):
        item = self.popupmenu.FindItemById(event.GetId())
        ip = self.GetSelectedIp()
        if len(ip) > 0:
            self.thread.putMessage(ip)
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


    def OnRightDown(self, event):
        pos = event.GetPosition()
        #pos = self.panel.ScreenToClient(pos)
        self.PopupMenu(self.popupmenu, pos)


    def OnClose(self, event):
        self.thread.putMessage("")
        self.thread.stop()
        self.Destroy()  # you may also do:  event.Skip()
                        # since the default event handler does call Destroy(), too

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scan goshimmer network')
    parser.add_argument('-node', type=str, default="188.68.53.235",
                        help='bootstrap node to start the scan')

    args = parser.parse_args()
    print(args.node)

    app = wx.App(0)
    frame = GridFrame(None, node=args.node)
    app.MainLoop()