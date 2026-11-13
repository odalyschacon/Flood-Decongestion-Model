"""WGS84 / UTM zone 14N transforms for the San Antonio pilot.

Series transverse-Mercator formulas, restricted to zone 14N, northern hemisphere.
Use a geospatial projection library for other regions. GIS work uses metre units.
"""
import numpy as np

A=6378137.0
E=0.0066943799901413165
K=0.9996
EP=E/(1-E)

def to_utm(lon,lat):
    lon,lat=np.asarray(lon,dtype=float),np.asarray(lat,dtype=float)
    if not (np.isfinite(lon).all() and np.isfinite(lat).all()): raise ValueError('Invalid coordinate')
    if ((lon < -102)|(lon > -96)|(lat < 0)|(lat > 84)).any(): raise ValueError('Outside UTM 14N')
    p=np.radians(lat); l=np.radians(lon+99)
    n=A/np.sqrt(1-E*np.sin(p)**2);t=np.tan(p)**2;c=EP*np.cos(p)**2;b=np.cos(p)*l
    m=A*((1-E/4-3*E**2/64-5*E**3/256)*p-(3*E/8+3*E**2/32+45*E**3/1024)*np.sin(2*p)+(15*E**2/256+45*E**3/1024)*np.sin(4*p)-35*E**3/3072*np.sin(6*p))
    x=500000+K*n*(b+(1-t+c)*b**3/6+(5-18*t+t*t+72*c-58*EP)*b**5/120)
    y=K*(m+n*np.tan(p)*(b*b/2+(5-t+9*c+4*c*c)*b**4/24+(61-58*t+t*t+600*c-330*EP)*b**6/720))
    return x,y

def to_lonlat(x,y):
    x,y=np.asarray(x,dtype=float),np.asarray(y,dtype=float)
    mu=(y/K)/(A*(1-E/4-3*E**2/64-5*E**3/256))
    e1=(1-np.sqrt(1-E))/(1+np.sqrt(1-E))
    p=mu+(3*e1/2-27*e1**3/32)*np.sin(2*mu)+(21*e1**2/16-55*e1**4/32)*np.sin(4*mu)+151*e1**3/96*np.sin(6*mu)+1097*e1**4/512*np.sin(8*mu)
    c=EP*np.cos(p)**2;t=np.tan(p)**2;n=A/np.sqrt(1-E*np.sin(p)**2)
    r=A*(1-E)/(1-E*np.sin(p)**2)**1.5;d=(x-500000)/(n*K)
    lat=p-(n*np.tan(p)/r)*(d*d/2-(5+3*t+10*c-4*c*c-9*EP)*d**4/24+(61+90*t+298*c+45*t*t-252*EP-3*c*c)*d**6/720)
    lon=(d-(1+2*t+c)*d**3/6+(5-2*c+28*t-3*c*c+8*EP+24*t*t)*d**5/120)/np.cos(p)
    return np.degrees(lon)-99,np.degrees(lat)
