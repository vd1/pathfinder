# Phase-matched counterexample and empirical boundary

Let \(w\) be wrist pose, \(e\) the seven motor-encoder readings, \(z\) a latent passive-joint/contact mode, and \(f\) object pose. Q's staged underactuation permits the same commanded tendon position to be accommodated by different passive joint deflections when contacts differ. This motivates, but does not empirically establish, two phase-matched states

\[
s_A=(w_0,e_0,z_A,f_A), \qquad s_B=(w_0,e_0,z_B,f_B), \qquad z_A\ne z_B.
\]

Choose \(z_A\) as a sticking power grasp and \(z_B\) as distal rolling or shared support. The required corrective action after the same wrist perturbation can differ even though the policy receives the same wrist and encoder observation. A local model is

\[
f=w h(z), \qquad \delta f=J_z\delta w,
\]

where both \(J_{z_A}\) and \(J_{z_B}\) can be nonzero, so the wrist causally influences the object in both states, while \(h(z_A)\ne h(z_B)\). Across phase-matched demonstrations containing both modes, the covariance of \(w^{-1}f=h(z)\) need not be small. P's statistic can therefore exceed its masking threshold even when the finite-horizon intervention score is high:

\[
M_t^{(f)}\ge \tau_M,
\qquad
I_{w\to f}(t)=
\frac{\mathbb E_{\delta w}\!\left[d\!\left(f_{t+\Delta}^{\operatorname{do}(w+\delta w)},f_{t+\Delta}\right)^2\right]}
{\mathbb E_{\delta w}\!\left[\lVert\delta w\rVert^2\right]}>\tau_I.
\]

This is a constructed identifiability counterexample, not a simulator result. The papers do not prove that a robust pair \((s_A,s_B)\) exists in Q's released model, and this workspace contains no simulator or DynaMAC implementation with which to test it. The minimal empirical test must:

1. save two simulator states at the same task phase with matched \((w_0,e_0)\) and distinct mechanically stable modes;
2. replay matched wrist perturbations under a fixed low-level feedback convention;
3. estimate \(I_{w\to f}\) and P's phase-indexed \(M_t^{(f)}\) without pooling phases;
4. establish that detector error precedes policy error; and
5. compare the fixed policy under P's mask and an oracle mask while retaining identical demonstrations and controllers.

An oracle-mask rescue would support the representation claim. Failure to construct stable aliased states, low measured intervention in the allegedly coupled mode, or no oracle rescue would reject or substantially weaken it.
