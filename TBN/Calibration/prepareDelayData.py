#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import ephem
import numpy

from datetime import datetime

from scipy.optimize import leastsq, fmin
from scipy.stats import pearsonr

from lsl.common.constants import c as vLight
from lsl.astro import unix_to_utcjd
from lsl.common.stations import lwa1
from lsl.correlator.uvUtils import computeUVW
from lsl.misc.mathutil import to_dB
from lsl.statistics import robust

import lsl.sim.vis as simVis


def main(args):
	observer = lwa1.getObserver()
	antennas = lwa1.getAntennas()
	nAnts = len(antennas)
	
	filenames = args
	
	data = []
	time = []
	freq = []
	for filename in filenames:
		dataDict = numpy.load(filename)
		
		refAnt = dataDict['ref']
		refX   = dataDict['refX']
		refY   = dataDict['refY']
		centralFreq = float(dataDict['centralFreq'])
		
		times = dataDict['times']
		phase = dataDict['simpleVis']
		
		beginDate = datetime.utcfromtimestamp(times[0])
		observer.date = beginDate.strftime("%Y/%m/%d %H:%M:%S")
		
		freq.append( centralFreq )
		time.append( unix_to_utcjd(times) )
		data.append( phase[0,:] )
		
	freq = numpy.array(freq)
	time = numpy.array(time)
	data = numpy.array(data)
	
	order = numpy.argsort(freq)
	freq = numpy.take(freq, order)
	time = numpy.take(time, order)
	data = numpy.take(data, order, axis=0)
		
	nFreq = len(freq)
	
	print "Reference stand #%i (X: %i, Y: %i)" % (refAnt, refX, refY)
	print "-> X: %s" % str(antennas[refX])
	print "-> Y: %s" % str(antennas[refY])
	
	print "Using a set of %i frequencies" % nFreq
	print "->", freq/1e6
	
	#
	# Initial parameter guesses
	#
	centralFreq = numpy.median( freq )

	p = numpy.zeros((2, len(antennas)))
	for i in xrange(len(antennas)):
		phi0 = 0.0
		tau = antennas[i].cable.delay(centralFreq)
		
		p[:,i] = [phi0, tau]

	refX = refX.item()
	refY = refY.item()

	#
	# Compute source positions/build the point-source model
	#
	simPhase = numpy.zeros_like(data)
	aa = simVis.buildSimArray(lwa1, antennas, freq)
	for i in xrange(freq.size):
		fq = freq[i]
		jd = time[i]
			
		## X pol.
		simDictX = simVis.buildSimData(aa, simVis.srcs, jd=jd, pols=['xx',], baselines=[(refX,l) for l in xrange(0,520,2)])
			
		diffFq = numpy.abs( simDictX['freq'] - fq )
		best = numpy.where( diffFq == diffFq.min() )[0][0]
			
		for l,vis in enumerate(simDictX['vis']['xx']):
			simPhase[i,2*l+0] = vis[best]
			
		## Y pol.
		simDictY = simVis.buildSimData(aa, simVis.srcs, jd=jd, pols=['yy',], baselines=[(refY,l) for l in xrange(1,520,2)])
			
		diffFq = numpy.abs( simDictX['freq'] - fq )
		best = numpy.where( diffFq == diffFq.min() )[0][0]
			
		for l,vis in enumerate(simDictY['vis']['yy']):
			simPhase[i,2*l+1] = vis[best]

	#
	# Save
	#
	numpy.savez('prepared-dat.npz', refAnt=refAnt, refX=refX, refY=refY, freq=freq, time=time, data=data, simPhase=simPhase)


if __name__ == "__main__":
	main(sys.argv[1:])