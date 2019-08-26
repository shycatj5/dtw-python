##
## Copyright (c) 2006-2019 of Toni Giorgino
##
## This file is part of the DTW package.
##
## DTW is free software: you can redistribute it and/or modify it
## under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## DTW is distributed in the hope that it will be useful, but WITHOUT
## ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
## or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public
## License for more details.
##
## You should have received a copy of the GNU General Public License
## along with DTW.  If not, see <http://www.gnu.org/licenses/>.
##



# Author: Toni Giorgino 2018
#
# If you use this software in academic work, please cite:
#  * T. Giorgino. Computing and Visualizing Dynamic Time Warping
#    Alignments in R: The dtw Package. Journal of Statistical
#    Software, v. 31, Issue 7, p. 1 - 24, aug. 2009. ISSN
#    1548-7660. doi:10.18637/jss.v031.i07. http://www.jstatsoft.org/v31/i07/




import numpy

from .stepPattern import *
from .backtrack import _backtrack
from .globalCostMatrix import _globalCostMatrix
from .window import *



from scipy.spatial.distance import cdist




# --------------------

class DTW:
    def __init__(self, obj):
        self.__dict__.update(obj) # Convert dict to object 

    def __repr__(self):
        s = "DTW alignment object of size (query x reference): {:d} x {:d}".format(self.N, self.M)
        return (s)


# --------------------


def dtw(x, y=None,
        dist_method="euclidean",
        step_pattern=symmetric2,
        window_type=None,
        window_args={},
        keep_internals=False,
        distance_only=False,
        open_end=False,
        open_begin=False):
    """Compute Dynamic Time Warp and find optimal alignment between two time series.

    Under development. The syntax mirrors the one in R 'dtw' package
    (please see links below), except that dots in argument names are
    replaced by underscores.

    Parameters
    ----------

    x : array_like
       First input. A timeseries (1D or higher dimension), with time in rows.
       If y = None, interpreted as the local distance matrix instead.
    y : array_like
       Second input. A timeseries (1D or higher dimension), with time in rows.
    dist_method : str, optional
       One of the distance metrics supported by scipy.spatial.distance.cdist
       Defaults to 'euclidean'
    step_pattern : object, optional
       An object representing the recursion form, i.e. local slope constraints.
       Currenly only symmetric1 and symmetric2 are implemented.
    distance_only : bool, optional
       Only compute the distance, not the alignment (may be slightly faster
       and memory-efficient)


    Returns
    -------
    alignment : object
        an instance of type DTW encapsulating the same properties as the R implementation (q.v.),
        and in particular see:
            .distance
            .costMatrix
            .index1 etc.

    See also
    --------
     * https://cran.r-project.org/web/packages/dtw/index.html
     * http://dtw.r-forge.r-project.org
     * https://www.rdocumentation.org/packages/dtw/versions/1.20-1/topics/dtw

    Citation
    --------
    If you use this software in academic work, please cite:

     * T. Giorgino. Computing and Visualizing Dynamic Time Warping
       Alignments in R: The dtw Package. Journal of Statistical
       Software, v. 31, Issue 7, p. 1 - 24, aug. 2009. ISSN
       1548-7660. doi:10.18637/jss.v031.i07. http://www.jstatsoft.org/v31/i07/

    Examples
    --------
    The worked-out exercise in section 3.9 of http://www.jstatsoft.org/v31/i07/ and
    Rabiner-Juang's book (Exercise 4.7 page 226).

    >>> from scipy.signal.dtw import *
    >>> lm = numpy.array( [[ 1,1,2,2,3,3 ],
                        [ 1,1,1,2,2,2 ],
                        [ 3,1,2,2,3,3 ],
                        [ 3,1,2,1,1,2 ],
                        [ 3,2,1,2,1,2 ],
                        [ 3,3,3,2,1,2 ]], dtype=numpy.double)
    >>> alignment = dtw(lm, step_pattern=asymmetric)
    >>> alignment.costMatrix

    """


    if y is None:
        x = numpy.array(x)
        if len(x.shape) != 2:
            raise ValueError("A 2D local distance matrix was expected")
        lm = numpy.array(x)
    else:
        x = numpy.atleast_2d(x)
        y = numpy.atleast_2d(y)
        if x.shape[0] == 1:
            x = x.T
        if y.shape[0] == 1:
            y = y.T
        lm = cdist(x, y, metric=dist_method)

        
    wfun = _canonicalizeWindowFunction(window_type)

    norm = step_pattern.hint

    n, m = lm.shape

    if open_begin:
        if norm != "N":
            error("Open-begin requires step patterns with 'N' normalization (e.g. asymmetric, or R-J types (c)). See Tormene et al.")
        lm = numpy.vstack( [ numpy.zeros((1,lm.shape[1])), lm ] ) # prepend null row
        np = n+1
        precm = numpy.full_like(lm, numpy.nan, dtype=numpy.double)
        precm[0,:] = 0
    else:
        precm = None
        np = n
    

    gcm = _globalCostMatrix(lm,
                            step_pattern=step_pattern,
                            window_function=wfun,
                            seed=precm,
                            win_args=window_args)
    gcm = DTW(gcm)              # turn into an object, use dot to access properties

    gcm.N = n
    gcm.M = m

    gcm.openEnd = open_end
    gcm.openBegin = open_begin
    gcm.windowFunction = wfun
    gcm.windowArgs = window_args           # py

    # misnamed
    lastcol = gcm.costMatrix[-1,]

    if norm == "NA":
        pass
    elif norm == "N+M":
        lastcol = lastcol/(n+numpy.arange(m)+1)
    elif norm == "N":
        lastcol = lastcol / n
    elif norm == "M":
        lastcol = lastcol / (1+numpy.arange(m))

    gcm.jmin = m-1

    if open_end:
        if norm == "NA":
            error("Open-end alignments require normalizable step patterns")
        gcm.jmin = numpy.argmin(lastcol)

    gcm.distance = gcm.costMatrix[-1, gcm.jmin]
        
    if gcm.distance != gcm.distance: # nan
        raise ValueError("No warping path found compatible with the local constraints")

    if step_pattern.hint != "NA":
        gcm.normalizedDistance = lastcol[gcm.jmin]
    else:
        gcm.normalizedDistance = numpy.nan

    if not distance_only:
        mapping = _backtrack(gcm)
        gcm.__dict__.update(mapping)

    if open_begin:
        gcm.index1 = gcm.index1[1:]-1
        gcm.index1s = gcm.index1s[1:]-1
        gcm.index2 = gcm.index2[1:]
        gcm.index2s = gcm.index2s[1:]
        lm = lm[1:,:]
        gcm.costMatrix = gcm.costMatrix[1:,:]
        gcm.directionMatrix = gcm.directionMatrix[1:,:]

    if not keep_internals:
        del gcm.costMatrix
        del gcm.directionMatrix
    else:
        gcm.localCostMatrix = lm
        if y is not None:
            gcm.query = x
            gcm.reference = y
        
    return gcm
            


# Return a callable object representing the window
def _canonicalizeWindowFunction(window_type):
    if callable(window_type):
        return window_type

    if window_type is None:
        return noWindow

    return {
        "none": noWindow,
        "sakoechiba": sakoeChibaWindow,
        "itakura": itakuraWindow,
        "slantedband": slantedBandWindow
    }.get(w, lambda: error("Window function undefined"))

