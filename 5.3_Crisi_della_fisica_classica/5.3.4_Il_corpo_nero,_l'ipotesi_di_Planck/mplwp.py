'''
mplwp, version 1.8
The Matplotlib extension for Wikipedia plots
requires: numpy, scipy, matplotlib, lxml
written by Geek3 @ commons.wikimedia.org
https://commons.wikimedia.org/wiki/User:Geek3/mplwp

Copyright (C) 2014 - 2019 Geek3

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation;
either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, see http://www.gnu.org/licenses/
'''
 
import string
import re
import scipy as sc
import numpy as np
from math import *
 
# we don't use pylab, but numpy and pyplot instead
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.path import Path
from matplotlib import scale as mscale
from matplotlib import transforms as mtransforms
from matplotlib.ticker import scale_range
import matplotlib.style
 
 
try:
    from lxml import etree
except ImportError, er:
    print 'ImportError:', er
    print 'You need to install lxml (http://lxml.de/)'
    exit(1)
 
 
commons_website = 'https://commons.wikimedia.org/wiki/File:'
color_cycle = ('#0000cc', '#dd00aa', '#999900', '#00bb00', '#00bbcc',
    '#af77dd', '#f46644', '#ebca10', '#d0f011', '#66f800', '#99eeff')
 
 
def unicode_sub(x):
    '''
    converts x into a subscript unicode string
    '''
    table = {'-': unichr(8331), '(':unichr(8333), ')':unichr(8334)}
    for i in range(9+1):
        table[str(i)] = unichr(8320+i)
    return ''.join([table[ch] for ch in str(x)])
 
 
def unicode_super(x):
    '''
    converts x into a superscript unicode string
    '''
    table = {'-': unichr(8315), '(':unichr(8317), ')':unichr(8318)}
    table['1'] = unichr(185)
    for i in range(2, 3+1):
        table[str(i)] = unichr(176+i)
    for i in [0] + range(4, 9+1):
        table[str(i)] = unichr(8304+i)
    return ''.join([table[ch] for ch in str(x)])
 
 
def set_bordersize(fig, l, r, t, b):
    '''
    sets borders around axes in pixels
    '''
    w, h = fig.get_size_inches() * fig.dpi
    bounds = [float(l)/w, float(b)/h, 1.0 - float(l+r)/w, 1.0 - float(t+b)/h]
    fig.gca().set_position(bounds)
 
 
def move_axes(fig, dx, dy):
    '''
    move current axes by the given number of pixels
    '''
    w, h = fig.get_size_inches() * fig.dpi
    bounds = fig.gca().get_position().get_points()
    bounds = (bounds[0,0] + float(dx)/w, bounds[0,1] + float(dy)/h,
        bounds[1,0] - bounds[0,0], bounds[1,1] - bounds[0,1])
    fig.gca().set_position(bounds)
 
 
def mark_axeszero(ax, x0=None, y0=None):
    '''
    marks the zero-gridlines with denser dash patterns
    Caution! This only works correctly if the gridlines won't change afterwards.
    '''
 
    # update gridline data
    ax.grid(True)
    ax.figure.canvas.draw()
    
    for l in ax.xaxis.get_gridlines():
        if ((x0 != None and np.isclose(l.get_xdata()[0], x0)) or (x0 == None and (
            (l.get_xdata()[0] == 0.0 and ax.get_xscale() == 'linear') or
            (l.get_xdata()[0] == 1e0 and ax.get_xscale() == 'log')))):
            l.set_dashes([3,1])
    
    for l in ax.yaxis.get_gridlines():
        if ((y0 != None and np.isclose(l.get_ydata()[0], y0)) or (y0 == None and (
            (l.get_ydata()[0] == 0.0 and ax.get_yscale() == 'linear') or
            (l.get_ydata()[0] == 1e0 and ax.get_yscale() == 'log')))):
            l.set_dashes([3,1])
 
 
def fig_standard(mpl):
 
    # global settings
    mpl.rcdefaults()
    mpl.style.use('classic')
    mpl.rc('font', size=16)
    mpl.rcParams['font.sans-serif'] = 'DejaVu Sans'
    mpl.rc('mathtext', default='regular')
    mpl.rc('lines', linewidth=2.4)
    mpl.rc('xtick.major', pad=7)
    mpl.rc('ytick.major', pad=7)
    mpl.rc('legend', borderaxespad=1.5)
    mpl.rc('lines', markersize=9.6)
    mpl.rc('lines', markeredgewidth=1.8)
    mpl.rc('path', simplify=True)
    mpl.rc('path', snap=False)
 
    fig = plt.figure()
    ax = fig.gca()
 
    # figure settings
    width = 600.
    height = 400.
    fig.set_dpi(72)
    fig.set_size_inches(width / fig.dpi, height / fig.dpi)
    ax.xaxis.set_major_locator(plt.MaxNLocator(nbins=11,
        steps=[1, 2, 2.5, 5], integer=False, symmetric=True, prune=None))
    ax.yaxis.set_major_locator(plt.MaxNLocator(nbins=10,
        steps=[1, 2, 5], integer=False, symmetric=True, prune=None))
 
    # axes settings
    # set image margins so that lines will be exactly on a pixel
    l, r, t, b = (42.5, 42.5, 18.5, 26.5)
    set_bordersize(fig, l, r, t, b)
    for axis in ['top','bottom','left','right']:
        ax.spines[axis].set_linewidth(1.25)
    ax.tick_params(width=1.25)
 
    ax.grid(True)
    ax.set_color_cycle(color_cycle)
    #mpl.rc('axes', prop_cycle=mpl.cycler(color=color_cycle)) 
 
    return fig
 
 
def remove_zeros(group, nsmap):
    for path in group.findall(nsmap + 'path'):
        try:
            d = path.get('d')
            # remove trailing zeros
            d = re.sub(r'(\d+)\.0+(?=$|[^\d])', r'\1', d) # 12.00 -> 12
            d = re.sub(r'\.0+(?=$|[^\d])', r'0', d) # .000 -> 0
            d = re.sub(r'((\d+\.\d*[1-9])|(\.\d*[1-9]))0+(?=$|[^\d])', r'\1', d) # 12.20300 -> 12.203
            # insert spaces around letters
            d = re.sub(r'([A-z])(\S)', r'\1 \2', d)
            path.set('d', d)
        except Exception:
            pass
 
    # recursive call
    for g in group.findall(nsmap + 'g') + group.findall(nsmap + 'defs'):
        remove_zeros(g, nsmap)
 
 
def file_replace_d(fname, old, new):
    f = open(fname, 'r')
    text = re.sub(r'd="[^"]*"', lambda x: x.group(0).replace(old, new), f.read())
    f.close()
    f = open(fname, 'w')
    f.write(text)
    f.close()
 
 
def postprocess(fname):
    '''
    postprocess svg file generated by matplotlib to fix some problems
    '''

    file_replace_d(fname, '\n', '#') # hide newlines from parser
    with open(fname, 'r') as svgfile:
        tree = etree.parse(svgfile, etree.XMLParser(remove_blank_text=True))
    svg = tree.getroot()
    nsmap = '{' + svg.nsmap[None] + '}'

    # define graphic size in pixels instead of pt
    for variable in ['width', 'height']:
        svg.set(variable, string.replace(svg.get(variable), 'pt', 'px'))

    # move all definitions to the front
    svg[:] = sorted(svg, key=lambda el: int(el.tag!=nsmap+'defs'))

    # add title and file description
    title = etree.Element('title')
    title.text = fname
    desc = etree.Element('desc')
    desc.text = commons_website + fname
    desc.text += '\nPlot created with mplwp, the Matplotlib extension for Wikipedia plots.'
    svg[:] = [title] + [desc] + svg[:]

    # remove unnecessary trailing zeros
    remove_zeros(svg, nsmap)

    # write back content
    with open(fname, 'w') as svgfile:
        tree.write(svgfile,
            xml_declaration=True, pretty_print=True, encoding='utf-8')
    file_replace_d(fname, '#', '\n') # write replaced newlines back
