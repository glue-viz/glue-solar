"""Line-by-line port of IDL lib spline.pro (IDL >= 6.1 copy from
github.com/leonf88/envi-spectrum lib/spline.pro), including its
monotonic-pointer interval search, to test what IDL does with decreasing T."""
import numpy as np


def idl_spline(x, y, t, sigma_in=1.0, dbl=True):
    ft = np.float64 if dbl else np.float32
    xx = np.asarray(x, ft); yy = np.asarray(y, ft); tt = np.atleast_1d(np.asarray(t, ft))
    n = min(xx.size, yy.size)
    sigma = ft(max(sigma_in, 0.001))
    yp = np.zeros(2 * n, ft)
    delx1 = xx[1] - xx[0]
    dx1 = (yy[1] - yy[0]) / delx1
    nm1 = n - 1
    delx2 = xx[2] - xx[1]; delx12 = xx[2] - xx[0]
    c1 = -(delx12 + delx1) / delx12 / delx1; c2 = delx12 / delx1 / delx2; c3 = -delx1 / delx12 / delx2
    slpp1 = c1 * yy[0] + c2 * yy[1] + c3 * yy[2]
    deln = xx[nm1] - xx[nm1 - 1]; delnm1 = xx[nm1 - 1] - xx[nm1 - 2]; delnn = xx[nm1] - xx[nm1 - 2]
    c1 = (delnn + deln) / delnn / deln; c2 = -delnn / deln / delnm1; c3 = deln / delnn / delnm1
    slppn = c3 * yy[nm1 - 2] + c2 * yy[nm1 - 1] + c1 * yy[nm1]
    sigmap = sigma * nm1 / (xx[nm1] - xx[0])
    dels = sigmap * delx1
    exps = np.exp(dels)
    sinhs = 0.5 * (exps - 1. / exps)  # 0.5d -> double
    sinhin = 1. / (delx1 * sinhs)
    diag1 = sinhin * (dels * 0.5 * (exps + 1. / exps) - sinhs)
    diagin = 1. / diag1
    yp[0] = diagin * (dx1 - slpp1)
    spdiag = sinhin * (sinhs - dels)
    yp[n] = diagin * spdiag
    d2 = xx[1:] - xx[:-1]
    dx2 = (yy[1:] - yy[:-1]) / d2
    dels = sigmap * d2
    exps = np.exp(dels)
    sinhs = 0.5 * (exps - 1. / exps)
    sinhin = 1. / (d2 * sinhs)
    diag2 = sinhin * (dels * (0.5 * (exps + 1. / exps)) - sinhs)
    diag2 = np.concatenate([[0], diag2[:-1] + diag2[1:]])
    dx2nm1 = dx2[nm1 - 1]
    dx2 = np.concatenate([[0], dx2[1:] - dx2[:-1]])
    spdiag = sinhin * (sinhs - dels)
    for i in range(1, nm1):
        diagin = 1. / (diag2[i] - spdiag[i - 1] * yp[i + n - 1])
        yp[i] = diagin * (dx2[i] - spdiag[i - 1] * yp[i - 1])
        yp[i + n] = diagin * spdiag[i]
    diagin = 1. / (diag1 - spdiag[nm1 - 1] * yp[n + nm1 - 1])
    yp[nm1] = diagin * (slppn - dx2nm1 - spdiag[nm1 - 1] * yp[nm1 - 1])
    for i in range(n - 2, -1, -1):
        yp[i] = yp[i] - yp[i + n] * yp[i + 1]
    m = tt.size
    subs = np.full(m, nm1)
    s = xx[nm1] - xx[0]
    sigmap = sigma * nm1 / s
    j = 0
    done = False
    for i in range(1, nm1 + 1):
        while tt[j] < xx[i]:
            subs[j] = i
            j += 1
            if j == m:
                done = True
                break
        if done:
            break
    subs1 = subs - 1
    del1 = tt - xx[subs1]; del2 = xx[subs] - tt; dels = xx[subs] - xx[subs1]
    exps1 = np.exp(sigmap * del1); sinhd1 = 0.5 * (exps1 - 1. / exps1)
    exps = np.exp(sigmap * del2); sinhd2 = 0.5 * (exps - 1. / exps)
    exps = exps1 * exps; sinhs = 0.5 * (exps - 1. / exps)
    spl = (yp[subs] * sinhd1 + yp[subs1] * sinhd2) / sinhs + ((yy[subs] - yp[subs]) * del1 + (yy[subs1] - yp[subs1]) * del2) / dels
    return spl, subs
