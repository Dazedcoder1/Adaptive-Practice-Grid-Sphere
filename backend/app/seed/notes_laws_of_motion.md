# Laws of Motion — Study Notes (Sample)

These notes accompany the sample CBSE Class 11 Physics chapter. Take $g = 10\ \text{m/s}^2$ throughout.

## Inertia and Newton's first law
<!-- concepts: N1 -->

**Inertia** is the tendency of a body to keep doing what it is already doing: a body at rest stays at rest, and a moving body keeps moving with the same velocity. Mass is the measure of inertia — the more mass a body has, the harder it is to change its motion.

**Newton's first law:** a body continues in its state of rest or of uniform motion in a straight line unless an external, unbalanced force acts on it.

The first law tells us what a force *does*: it changes velocity. If the net force on a body is zero, its velocity is constant (which includes being at rest). It does **not** say that motion needs a force — a puck sliding on smooth ice keeps going without one.

Everyday examples: passengers lurch forward when a bus brakes suddenly (their bodies tend to keep moving), and dust leaves a carpet when it is beaten (the carpet moves, the dust tends to stay at rest).

## Linear momentum
<!-- concepts: MOM -->

The **linear momentum** of a body is the product of its mass and velocity:

$$\vec p = m\vec v$$

Momentum is a vector, in the direction of the velocity, with SI unit kg·m/s. A slow, heavy truck and a fast, light bullet can have similar momenta.

When no external force acts on a system, its total momentum stays constant. This is the **conservation of linear momentum**. For example, when a gun of mass $M$ fires a bullet of mass $m$ with velocity $v$, the gun recoils with velocity $V = -\dfrac{mv}{M}$, because the total momentum was zero before firing and must stay zero.

## Newton's second law (F = ma)
<!-- concepts: N2 -->

**Newton's second law:** the rate of change of momentum of a body equals the net external force on it, and is in the direction of that force:

$$\vec F_{\text{net}} = \frac{d\vec p}{dt}$$

For a body of constant mass this becomes

$$\vec F_{\text{net}} = m\vec a$$

The SI unit of force is the **newton** (N): $1\ \text{N} = 1\ \text{kg·m/s}^2$.

Key points:

- Use the **net** force — the vector sum of all forces on the body, not just one of them.
- The acceleration is in the direction of the net force, which need not be the direction of motion.
- The law holds component by component: $F_x = ma_x$ and $F_y = ma_y$.

Worked example: a net force of 12 N acts on a 3 kg block. Its acceleration is $a = F/m = 12/3 = 4\ \text{m/s}^2$. If the block starts from rest, after 2 s its speed is $v = at = 8\ \text{m/s}$.

A common mistake is to treat mass and acceleration as the same thing. Mass is a property of the body; acceleration depends on the net force acting on it at that moment.

## Impulse
<!-- concepts: IMP -->

When a large force acts for a short time — a bat hitting a ball, a hammer striking a nail — it is easier to work with **impulse**, the product of force and the time it acts:

$$\vec J = \vec F\,\Delta t = \Delta \vec p$$

Impulse equals the change in momentum (the **impulse–momentum theorem**), so its unit, N·s, is the same as kg·m/s.

For a given change in momentum, a longer contact time means a smaller force. This is why a cricketer draws the hands back while catching a ball, and why vehicles have crumple zones and airbags: they stretch out the stopping time and so reduce the force.

Example: a 0.15 kg ball moving at 20 m/s is stopped in 0.05 s. The change in momentum is $0.15 \times 20 = 3\ \text{kg·m/s}$, so the average force is $3 / 0.05 = 60\ \text{N}$.

## Newton's third law
<!-- concepts: N3 -->

**Newton's third law:** to every action there is an equal and opposite reaction. Whenever body A exerts a force on body B, body B exerts a force on body A that is equal in size and opposite in direction.

The two forces of an action–reaction pair:

- act on **different** bodies, so they never cancel each other out;
- are of the same kind (both gravitational, both contact forces, and so on);
- act at the same time — neither one causes the other.

When you walk, your foot pushes the ground backwards and the ground pushes you forwards. A rocket pushes exhaust gases backwards and the gases push the rocket forwards.

The weight of a book on a table and the table's normal force on the book are **not** a third-law pair: both act on the book. The pair of the book's weight is the book's gravitational pull on the Earth.

## Free-body diagrams
<!-- concepts: FBD -->

A **free-body diagram** shows one body on its own, with every force that acts *on* it drawn as an arrow from the body. It is the first step in almost every laws-of-motion problem.

How to draw one:

1. Choose the body (or system) and draw it as a simple box or dot.
2. Add the weight $mg$, acting vertically downwards.
3. Add a contact force wherever something touches the body: the normal force (perpendicular to the surface), friction (along the surface), tension (along a string, pulling away from the body).
4. Add any applied forces.
5. Choose axes — usually along and perpendicular to the direction of acceleration — and resolve forces into components.

Only include forces acting **on** the chosen body. Forces the body exerts on other things belong on *their* diagrams.

## Equilibrium of a particle
<!-- concepts: EQ -->

A particle is in **equilibrium** when the net force on it is zero. It is then either at rest or moving with constant velocity.

For forces in a plane, equilibrium means

$$\sum F_x = 0 \qquad \text{and} \qquad \sum F_y = 0$$

Three forces in equilibrium can be drawn head to tail to form a closed triangle. A lamp hanging from two strings, or a box resting on a ramp without sliding, are equilibrium problems: draw the free-body diagram, resolve the forces and set each component sum to zero.

Example: a 2 kg mass hangs at rest from a single string. The tension balances the weight, so $T = mg = 2 \times 10 = 20\ \text{N}$.

## Friction
<!-- concepts: FRIC -->

**Friction** is the contact force that opposes relative motion (or the tendency of relative motion) between surfaces in contact. It acts along the surface.

- **Static friction** adjusts itself to stop sliding, up to a maximum value $f_s^{\max} = \mu_s N$.
- **Kinetic friction** acts once sliding has started: $f_k = \mu_k N$, and usually $\mu_k < \mu_s$.

Here $N$ is the normal force and $\mu$ is the coefficient of friction, which depends on the pair of surfaces, not on the area of contact.

A block of mass $m$ on a horizontal floor has $N = mg$. If $\mu_s = 0.4$ and $m = 5\ \text{kg}$, the largest push that leaves it at rest is $0.4 \times 5 \times 10 = 20\ \text{N}$.

On a slope of angle $\theta$ the normal force is $N = mg\cos\theta$, not $mg$. A block just begins to slide when $\tan\theta = \mu_s$.

## Connected bodies
<!-- concepts: CONN -->

Bodies joined by light, inextensible strings or pushing on each other move with the same acceleration. Two methods work together:

1. **Treat the system as one body** to find the acceleration: $a = \dfrac{F_{\text{net, external}}}{m_{\text{total}}}$. Internal forces such as the tension in the connecting string cancel out.
2. **Draw a free-body diagram for one body** to find an internal force such as tension.

Example: blocks of 2 kg and 3 kg on a smooth floor are joined by a string and pulled by 10 N applied to the 3 kg block. The system accelerates at $a = 10/5 = 2\ \text{m/s}^2$. The string is the only horizontal force on the 2 kg block, so the tension is $T = 2 \times 2 = 4\ \text{N}$.

For two masses hanging over a light, frictionless pulley (an Atwood machine), $a = \dfrac{(m_1 - m_2)g}{m_1 + m_2}$.

## Dynamics of circular motion
<!-- concepts: CIRC -->

A body moving in a circle at constant speed is still accelerating, because the direction of its velocity keeps changing. The acceleration points towards the centre:

$$a_c = \frac{v^2}{r}$$

By the second law there must be a net force towards the centre, the **centripetal force** $F_c = \dfrac{mv^2}{r}$. It is not a new kind of force — it is provided by tension, friction, gravity or a normal force.

- A stone whirled on a string: tension provides it.
- A car turning on a level road: friction between tyres and road provides it, so the maximum safe speed is $v_{\max} = \sqrt{\mu_s r g}$.
- On a banked road, a component of the normal force helps, so cars can turn faster.

Example: a 1000 kg car takes a 50 m radius turn at 10 m/s. The friction needed is $mv^2/r = 1000 \times 100 / 50 = 2000\ \text{N}$.
