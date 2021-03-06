#!/usr/bin/python
# -*- coding: utf-8 -*-
from types import *
import os, sys, xmpp, time, xmpp, threading
from datetime import datetime
from optparse import make_option
from django.conf import settings
from chat.models import Message, ResourcesStatuse

def presenceCB(conn,presence):
    if presence.getType()=='subscribe':
        jid = presence.getFrom().getStripped()
        conn.send(xmpp.protocol.Presence(jid,"subscribed"))
        print "User " + str(jid) + " authorized successful."

def messageCB(conn, mess):
    text = mess.getBody()
    if type(text) is NoneType:
        return
    user = mess.getFrom()
    username = unicode(user)
    resource_name = conn._owner.Resource
    date_time = datetime.now()
    resource = ResourcesStatuse.objects.get(name=resource_name)
    Message.objects.create(
                           resource     = resource,
                           date_time    = date_time,
                           message      = text,
                           direction    = 2
                           )
    
def run_xmpp_client(jabber_resource):
    try:
        jid=xmpp.JID(settings.JABBER_ID)
        user, server, password=jid.getNode(), jid.getDomain(), settings.JABBER_PASSWORD
            
        conn=xmpp.Client(server,debug=[])
        conres=conn.connect()
        
        if not conres:
            print "Unable to connect to server %s!"%server
            sys.exit(1)
            
        if conres<>'tls':
            print "Warning: unable to establish secure connection - TLS failed!"
            
        authres=conn.auth(user, password, jabber_resource)
        
        if not authres:
            print "Unable to authorize on %s - check login/password." % server
            sys.exit(1)
            
        if authres <> 'sasl':
            print "Warning: unable to perform SASL auth os %s. Old authentication method used!" % server
            
        conn.RegisterHandler('message', messageCB)
        conn.RegisterHandler('presence', presenceCB)
        conn.sendInitPresence()
                
        try:
            resource        = ResourcesStatuse.objects.get(name=jabber_resource)
            resource.status = 1
            resource.save()
        except:
            resource = ResourcesStatuse.objects.create(name=jabber_resource, status=1)
                
        print 'XMPP client started for resource "%s" successfully\n' % jabber_resource
                
        while resource.status != 2:
            conn.Process(1)
            # Проверка активности соединения
            if not conn.isConnected():
                conn.reconnectAndReauth()
            # Проверка активности ресурса
            ResourcesStatuse.objects.update()
            resource = ResourcesStatuse.objects.get(name=jabber_resource)
            # Поиск и если это нужно - отправка непрочитанных сообщений для администратора в этом ресурсе
            messages_to_admin = Message.objects.filter(resource=resource).filter(direction=1).filter(status=2)
            for message in messages_to_admin:
                m = xmpp.protocol.Message(to=settings.JABBER_RECIPIENT, body=message, typ='chat')
                conn.send(m)
                message.status=1
                message.save()
        else:
            resource.status=2
            resource.save()
            print 'XMPP client stopped for resource "%s" successfully\n' % jabber_resource
    except:
        print 'ERROR starting XMPP client!\n'
        raise

class StartXMPPClient(threading.Thread):

    def __init__(self, jabber_resource):
        self.jabber_resource = jabber_resource
        threading.Thread.__init__(self)

    def run(self):
        run_xmpp_client(self.jabber_resource)
