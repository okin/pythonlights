#!/usr/bin/python

from flask import Flask, render_template, redirect, request, make_response
import pythonlights as pl

plugin_error = None
try:
    from plugins import *
except Exception as e:
    print(e)
    plugin_error = e
import thread
import time
import os
import os.path
import subprocess
import sys
import json

log = open(os.path.dirname(os.path.realpath(__file__)) + "/interface.log", 'a')
sys.stdout = sys.stderr = log

app = Flask(__name__)

base_path = '/light'
pm = pl.LEDPluginMaster()

debug = False


@app.route("/")
@app.route("/index.html")
def interface():
    plugins = pm.plugins[:]
    plugins.reverse()
    return render_template('interface.html', now=time.time(), colors=pm.color_state, plugins=pm.available_plugins(), active_plugins=plugins,
                           presets=pm.available_presets(), plugin_error=(plugin_error != None), debug=debug)


@app.route("/error/")
def error():
    if plugin_error is not None:
        raise plugin_error
    return redirect(base_path)


@app.route("/help/")
def help():
    return render_template("help.html")


@app.route("/create/<plugin>/")
def create(plugin):
    pm.instanciate_plugin(plugin, priority=1)
    return redirect(base_path)


@app.route("/loadpreset/<preset>/")
def loadpreset(preset):
    pm.run_preset(preset)
    return redirect(base_path)


@app.route("/klingel/")
def klingel():
    pm.instanciate_plugin("Alert", priority=100, decay=time.time() + 10, mapping=range(0, 25, 2))
    return redirect(base_path)


@app.route("/delete/<pluginid>/")
def delete(pluginid):
    pm.remove_plugin(int(pluginid))
    return redirect(base_path)


@app.route("/setpriority/<pluginid>/<priority>/")
def setpriority(pluginid, priority):
    pm.get_plugin(int(pluginid)).priority = int(priority)
    pm.sort()
    return redirect(base_path)


@app.route("/setoption/<pluginid>/", methods=['POST'])
def setoption(pluginid):
    for option in request.form:
        pm.get_plugin(int(pluginid)).set_option(option, request.form[option])
    return redirect(base_path)

@app.route("/api/colors.json")
def get_colors_as_json():
    """
     build a dict to expose the current global and invidiual plugin colors as a json object
    """
    out = {"global": {}, "plugins": {}}

    # global
    for index, color in pm.color_state.iteritems():
        if type(color) is pl.Color:
            out["global"][index] = pl.Color.to_html(color.get_color())
        else:
            print("Type: %s" % type(color))
            out["global"][index] = None

    # plugins
    for plugin in pm.plugins:
        id = plugin.id
        out["plugins"][id] = {}
        # out["plugins"][id][index]
        for index, color in enumerate(plugin.state):
            if type(color) is pl.Color:
                out["plugins"][id][plugin.mapping[index]] = {"color": pl.Color.to_html(color.get_color()),
                                                             "label": pl.Color.to_html(color.get_complementary_color())}
    return json.dumps(out)


@app.route("/restart/")
def restart():
    try:
        return render_template('reload.html')
    finally:
        subprocess.Popen(["/etc/init.d/pythonlights", "restartslow"])


if __name__ == '__main__':
    thread.start_new_thread(pm.run, ())
    app.run(host='0.0.0.0', debug=True, use_reloader=False)
