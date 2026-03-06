Let's look at the corner where we change Y direction (from top to bottom). We need Y correction (go down for h) here.

Before corner we go up at $\alpha_1$, after go down at $\alpha_1$ (we need $tan \alpha$ only).

We replace top of the corner with horizontal line of length L connecting left and right lines (cut top of the edge) and perform correction (go down by h which will be eaten by backlash) during this line (because of correction in horizontal axis is invisible).

$j \le {jerk \over v}$

$0 < \tan \alpha_1 < j$


$$
-j < {h \over L} + \tan \alpha_1 < j
$$

$$
-j < {h \over L} - \tan \alpha_2 < j
$$

thus

$$
L > {h \over j - \tan \alpha_1}
$$

$$
\begin{cases}
L > \dfrac{h}{j + \tan \alpha_2}, & \text{if } \tan \alpha_2 \le j, \\
\dfrac{h}{j + \tan \alpha_2} < L < \dfrac{h}{\tan \alpha_2 - j}, & \text{if } \tan \alpha_2 > j
\end{cases}
$$

thus

$$
L > \max \left(
\frac{h}{j - \tan \alpha_1},
\frac{h}{j + \tan \alpha_2}
\right)
$$

$$
\text{if } \tan \alpha_2 > j,\ \text{then also }
L < \frac{h}{\tan \alpha_2 - j}
$$

L is divided into two parts – $L_1$ and $L_2$ for two segments.

$L_1 + L_2 = L$

$L_1 \tan \alpha_1 = L_2 \tan \alpha_2$

$L_1 = { L \tan \alpha_2 \over \tan \alpha_1 + \tan \alpha_2 }, L_2 = { L \tan \alpha_1 \over \tan \alpha_1 + \tan \alpha_2 }$

So offset left to $L_1$ (by line), right by $L_2$ (by line) and insert horizontal line. It will cut top

$h_1 = h_2 = { L \tan \alpha_1 \cdot \tan \alpha_2 \over \tan \alpha_1 + \tan \alpha_2 }$

of corner. Typical values for h = 0.35, $\tan \alpha_1 = \tan \alpha_2 = j/2$, $v=40, jerk=10$:

$L = { h \over j/2 } = 2.8$, $h_1 = h_2 = h/2 = 0.175$ – basically Ok for processing circles $r<11.2$.
