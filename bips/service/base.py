#REST webservice
import json
import os
import shutil
import webbrowser

import cherrypy
from cherrypy.lib.static import serve_file
from cherrypy import expose

from ..workflows import get_workflows, get_workflow

MEDIA_DIR = os.path.join(os.path.dirname(__file__), 'scripts')
FILE_DIR = os.path.join(os.getcwd(), 'files')

class MyEncoder(json.JSONEncoder):
    def default(self, o):
        """Implement this method in a subclass such that it returns
        a serializable object for ``o``, or calls the base implementation
        (to raise a ``TypeError``).

        For example, to support arbitrary iterators, you could
        implement default like this::

            def default(self, o):
                try:
                    iterable = iter(o)
                except TypeError:
                    pass
                else:
                    return list(iterable)
                return JSONEncoder.default(self, o)

        """
        try:
            return super(MyEncoder, self).default(o)
        except TypeError:
            return ""

class BIPS:
    @expose
    def index(self):
        msg = ["<h2>Welcome to BIPS</h2>"]
        msg.append('<ul>')
        for wf, value in get_workflows():
            msg += [('<li><a href="info?uuid=%s">%s</a> <a href="configure'
                     '?uuid=%s">Configure</a> %s</li>') % (wf, wf, wf,
                                        value['object'].help.split('\n')[1])]
        msg.append('</li>')
        return '\n'.join(msg)

    @expose
    def info(self, uuid):
        wf = get_workflow(uuid)
        val = wf.get()
        json_str =  json.dumps(val, cls=MyEncoder)
        config_str = json.dumps(wf.config_ui().get(), cls=MyEncoder)
        img_file = ''
        msg = """
<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="content-type" content="text/html; charset=UTF-8">
  <title> BIPS: Workflow info</title>
  <style type='text/css'>
    pre {outline: 1px solid #ccc; padding: 5px; margin: 5px; }
.string { color: green; }
.number { color: darkorange; }
.boolean { color: blue; }
.null { color: magenta; }
.key { color: red; }

  </style>
</head>
<body>

<script type="text/javascript">
function syntaxHighlight(json) {
    json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
        var cls = 'number';
        if (/^"/.test(match)) {
            if (/:$/.test(match)) {
                cls = 'key';
            } else {
                cls = 'string';
            }
        } else if (/true|false/.test(match)) {
            cls = 'boolean';
        } else if (/null/.test(match)) {
            cls = 'null';
        }
        return '<span class="' + cls + '">' + match + '</span>';
    });
}

var str = JSON.stringify(%s, null, 2);
document.write('<h3>Workflow info</h3>')
document.write('<pre>' + syntaxHighlight(str) +'</pre>');
var str2 = JSON.stringify(%s, null, 2);
document.write('<h3>Workflow config</h3>')
document.write('<pre>' + syntaxHighlight(str2) +'</pre>');
document.write('<h3>Workflow graph</h3>')
document.write('<img src="%s" />')
</script>

</body>


</html>
""" % (json_str, config_str, img_file)
        return msg

    @expose
    def configure(self, uuid):
        wf = get_workflow(uuid)
        val = wf.get()

    @expose
    def test(self):
        with open(os.path.join(MEDIA_DIR, 'upload.html')) as fp:
            msg = fp.readlines()
        return msg

    @expose
    def uploadhandler(self, **kwargs):
        if 'files[]' not in kwargs:
            return
        myFile = kwargs['files[]']
        outfile = os.path.join(FILE_DIR, myFile.filename)
        with open(outfile, 'wb') as fp:
            shutil.copyfileobj(myFile.file, fp)
        cherrypy.log('Saved file: %s' % outfile)
        if os.path.isfile(outfile):
            print "getting info: %s" % outfile
            size = os.path.getsize(outfile)
            from nibabel import load
            import Image
            import numpy as np
            data = load(outfile).get_data()
            if len(data.shape) == 4:
                slice = data[data.shape[0]/2,:,:,0]
            else:
                slice = data[data.shape[0]/2,:,:]
            print slice.shape
            im = Image.fromarray(np.squeeze(255.*slice/np.max(np.abs(slice))).astype(np.uint8))
            outpng = outfile+'.png'
            im.save(outpng)
            url_prefix = '\/\/bips.incf.org:8080\/'
            out = {"name": myFile.filename,
                   "size": size,
                   "url": "%sfiles\/%s" % (url_prefix, myFile.filename),
                   "thumbnail_url":"%sthumbnails\/%s.png" % (url_prefix, myFile.filename),
                   "delete_url": "%sdeletehandler?file=%s" % (url_prefix, myFile.filename),
                   "delete_type": "DELETE"
            }
        else:
            out = {}
        cherrypy.response.headers['Content-Type'] = 'application/json'
        return json.dumps([out])

    @expose
    def deletehandler(self, file):
        outfile = os.path.join(FILE_DIR, file)
        if os.path.isfile(outfile):
            cherrypy.log('Deleting file: %s' % outfile)
            os.unlink(outfile)
            os.unlink(outfile+'.png')

def open_page():
    pass
    #webbrowser.open("http://127.0.0.1:8080/test")

def start_service():
    #configure ip address and port for web service
    if not os.path.exists(FILE_DIR):
        os.mkdir(FILE_DIR)
    config = {'/': {'tools.staticdir.on': True,
                    'tools.staticdir.dir': os.getcwd()},
              '/css': {'tools.staticdir.on': True,
                       'tools.staticdir.dir': os.path.join(MEDIA_DIR, 'css')},
              '/js': {'tools.staticdir.on': True,
                      'tools.staticdir.dir': os.path.join(MEDIA_DIR, 'js')},
              '/cors': {'tools.staticdir.on': True,
                        'tools.staticdir.dir': os.path.join(MEDIA_DIR, 'cors')},
              '/img': {'tools.staticdir.on': True,
                       'tools.staticdir.dir': os.path.join(MEDIA_DIR, 'img')},
              '/thumbnails': {'tools.staticdir.on': True,
                       'tools.staticdir.dir': FILE_DIR},
              '/files': {'tools.staticdir.on': True,
                         'tools.staticdir.dir': FILE_DIR},
              }
    #start webservice
    certfile = os.path.join(os.environ['HOME'], 'certinfo')
    if os.path.exists(certfile):
        cherrypy.log('Loading cert info: %s' % certfile)
        cherrypy.config.update(json.load(open(certfile)))
    else:
        cherrypy.log('Cert info unavailable')
    cherrypy.engine.subscribe('start', open_page)
    cherrypy.tree.mount(BIPS(), '/', config=config)
    cherrypy.engine.start()
    cherrypy.engine.block()
    #cherrypy.quickstart(BIPS())
