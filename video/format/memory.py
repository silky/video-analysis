'''
Created on Jul 31, 2014

@author: zwicker

This package provides class definitions for describing videos
that are stored in memory using numpt arrays
'''

from __future__ import division

from .base import VideoBase

class VideoMemory(VideoBase):
    
    def __init__(self, data, fps=25):
        self.data = data
        
        frame_count = data.shape[0]
        size = data.shape[1:3]
        
        super(VideoMemory, self).__init__(size=size, frame_count=frame_count, fps=fps)
        
        
    def get_frame(self, index):
        frame = self.data[index, :, :, :]
        self._frame_pos = index + 1
        return frame
