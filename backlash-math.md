Let look at the corner where we change Y direction (from top to bottom). We need Y correction (go down for h) here.

Before corner we go up at $\alpha_1$, after go down at $\alpha_1$ (we need $tan \alpha$ only).

We replace top of the corner with horizontal line of length L connecting left and right lines (cut top of the edge) and perform correction (go down by h which will be eaten by backlash) during this line (because of correction in horizontal axis is invisible).

$j \le {jerk \over v}$

$0 < \tan \alpha_1 < j$, $0 < tan \alpha_2 < j$

|  limit      |  limit      |L            |             |
|-------------|-------------|-------------|-------------|
| $-j < {h \over L} + \tan \alpha_1 < j$  | $-j - \tan \alpha_1 < {h \over L} < j - \tan \alpha_1$  |  $L > {h \over -j - tan \alpha_1}$ |  $L > {h \over j - \tan \alpha_1}$ |
| $-j < {h \over L} - \tan \alpha_2 < j$  | $-j + \tan \alpha_2 < {h \over L} < j + \tan \alpha_2$  |  $L < {h \over \tan \alpha_2 - j}$ | $L > {h \over \tan \alpha_2 + j}$ |

