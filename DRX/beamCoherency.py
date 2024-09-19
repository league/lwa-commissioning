#!/usr/bin/env python3

"""
Given two or more DRX files from different beams, check for coherency between the beams
and make sure that the beams agree with the T_NOM values.
"""

import os
import sys
import numpy

from lsl.reader import drx
from lsl.common.dp import fS
from lsl.astro import unix_to_utcjd, DJD_OFFSET

from matplotlib import pyplot as plt


def crossCorrelate(sig, ref):
    """
    Cross-correlate two signals to get the lag between the two
    in samples.  Returns a two-element tuple of the lag values 
    in samples and the strength of the correlation.
    """
    
    cc = numpy.fft.fft(sig)*numpy.fft.fft(ref).conj()
    cc = numpy.abs(numpy.fft.fftshift(numpy.fft.ifft(cc)))
    lag = numpy.arange(-len(cc)/2,len(cc)/2)
    
    return lag, cc


def main(args):
    files = args
    
    fh = []
    nFramesFile = []
    srate = []
    beams = []
    tunepols = []
    beampols = []
    tnom = []
    tStart = []
    
    # Open the various files and get basic data information:  beam, number of 
    # frames per obs, T_NOM, time tag of first frame
    for filename in files:
        fh.append( open(filename, "rb") )
        nFramesFile.append( os.path.getsize(filename) / drx.FRAME_SIZE )
        
        while True:
            junkFrame = drx.read_frame(fh[-1])
            try:
                srate = junkFrame.sample_rate
                break
            except ZeroDivisionError:
                pass
        fh[-1].seek(-drx.FRAME_SIZE, 1)
    
        beam, tune, pol = junkFrame.id
        beams.append( beam )
        tunepols.append( drx.get_frames_per_obs(fh[-1]) )
        tunepols.append( tunepols[-1][0] + tunepols[-1][1] + tunepols[-1][2] + tunepols[-1][3] )
        beampols.append( tunepols[-1] )
        
        tnom.append( junkFrame.header.time_offset )
        tStart.append( junkFrame.payload.timetag )
    
    # Align the files as close as possible by the time tags and then make sure that
    # the first frame processed is from tuning 1, pol 0.
    for i in range(len(files)):
        junkFrame = drx.read_frame(fh[i])
        beam, tune, pol = junkFrame.id
        pair = 2*(tune-1) + pol
        j = 0
        while junkFrame.payload.timetag < max(tStart):
            junkFrame = drx.read_frame(fh[i])
            beam, tune, pol = junkFrame.id
            pair = 2*(tune-1) + pol
            j += 1
        while pair != 0:
            junkFrame = drx.read_frame(fh[i])
            beam, tune, pol = junkFrame.id
            pair = 2*(tune-1) + pol
            j += 1
        fh[i].seek(-drx.FRAME_SIZE, 1)
        print("Shifted beam %i data by %i frames (%.4f s)" % (i, j, j*4096/srate[i]/4))
            
    # Date
    beginDate = junkFrame.time.datetime

    # File summary
    print(" ")
    print("Filenames: %s" % ' '.join([os.path.split(f)[1] for f in files]))
    print("Date of First Frame: ~%s" % str(beginDate))
    print("Beams: %s" % ' '.join([str(b) for b in beams]))
    print("Sample Rate: %s Hz" % ' '.join([str(s) for s in srate]))
    print(" ")

    # Main reader loop - save the data to the `data` list and the raw time tag values
    # to the `times` list.
    nFrames = 2000
    data = numpy.zeros((len(files), 4, 4096*nFrames), dtype=numpy.csingle)
    times = numpy.zeros((len(files), 4, nFrames), dtype=numpy.int64)
    for i in range(len(files)):
        for j in range(nFrames):
            for k in range(4):
                frame = drx.read_frame(fh[i])
                beam, tune, pol = frame.id
                pair = 2*(tune-1) + pol
                
                data[i,pair,j*4096:(j+1)*4096] = frame.payload.data
                times[i,pair,j] = frame.payload.timetag
                #print(i, j, k, beam, tune, pol, frame.payload.timetag)
    
    # Cross-correlate
    refs = [0,0,0,0]
    for i in range(len(files)):
        for j in range(i, len(files)):
            if i != j:
                fig = plt.figure()
            
            for k in range(4):
                lag, cc = crossCorrelate(data[j,k,:], data[i,k,:])
                best = numpy.where( cc == cc.max() )[0][0]
                
                if i == j:
                    refs[k] = cc.max()
                else:
                    ccOffset = lag[best]*fS/srate[i]
                    rtOffset = times[i,k,0] - times[j,k,0]
                    ctOffset = (times[i,k,0] - tnom[i]) - (times[j,k,0] - tnom[j])
                    
                    print("Beams %i & %i, Tuning %i, Pol. %i" % (beams[i], beams[j], k/2+1, k%2))
                    print("  T_NOM%i: %i ticks" % (beams[i], tnom[i]))
                    print("  T_NOM%i: %i ticks" % (beams[j], tnom[j]))
                    print("  -> T_NOM%i - T_NOM%i: %i ticks" % (beams[j], beams[i], tnom[j] - tnom[i]))
                    print("  NCM: %.3f" % (cc.max() / refs[k]))
                    print("  CC Offset: %i ticks" % ccOffset)
                    print("  raw time tag Offset: %i ticks" % rtOffset)
                    print("  cor time tag Offset: %i ticks" % ctOffset)
                    print("  -> CC - raw: %i ticks" % (ccOffset - rtOffset))
                    print("  -> CC - cor: %i ticks" % (ccOffset - ctOffset))
                
                    ax = fig.add_subplot(2, 2, k+1)     # pylint: disable=possibly-used-before-assignment
                    ax.plot(lag[best-50:best+50], cc[best-50:best+50])
                    ax.set_title('Beams %i & %i, Tuning %i, Pol. %i' % (beams[i], beams[j], k/2+1, k%2))
                    ax.set_xlabel('Lag [samples]')
                    ax.set_ylabel('Analysis Sets')
            if i != j:
                plt.draw()
    plt.show()
    
    for f in fh:
        f.close()
        
    

if __name__ == "__main__":
    main(sys.argv[1:])
    
