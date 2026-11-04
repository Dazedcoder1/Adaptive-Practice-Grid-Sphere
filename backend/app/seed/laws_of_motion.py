"""SAMPLE content: CBSE Class 11 Physics — Motion in a Straight Line (prerequisite) and
Laws of Motion. Clearly flagged `is_sample`; edit or archive it in the admin portal.
g = 10 m/s² wherever gravity appears, stated in each question."""

CURRICULUM = {
    "format": "adaptivelearn.curriculum/v1",
    "name": "CBSE Class 11 (Sample)",
    "version": "2026-27-sample",
    "board": "CBSE",
    "grade": "Class 11",
    "subjects": [
        {
            "code": "PHY",
            "name": "Physics",
            "chapters": [
                {
                    "name": "Motion in a Straight Line",
                    "topics": [
                        {
                            "name": "Kinematics",
                            "concepts": [
                                {
                                    "code": "KIN",
                                    "name": "Acceleration and equations of motion",
                                    "description": (
                                        "**Acceleration** is the rate of change of velocity: $a = \\dfrac{\\Delta v}"
                                        "{\\Delta t}$, measured in m/s².\n\nFor constant acceleration:\n\n"
                                        "$$v = u + at \\qquad s = ut + \\tfrac{1}{2}at^2 \\qquad v^2 = u^2 + 2as$$\n\n"
                                        "where $u$ is the initial velocity, $v$ the final velocity, $s$ the "
                                        "displacement and $t$ the time."
                                    ),
                                    "prerequisites": [],
                                },
                            ],
                        }
                    ],
                },
                {
                    "name": "Laws of Motion",
                    "topics": [
                        {
                            "name": "Newton's laws of motion",
                            "concepts": [
                                {
                                    "code": "N1",
                                    "name": "Inertia and Newton's first law",
                                    "description": (
                                        "A body stays at rest, or keeps moving in a straight line at constant "
                                        "speed, unless a **net external force** acts on it.\n\n**Inertia** is "
                                        "the resistance of a body to a change in its state of motion. Mass is "
                                        "the measure of inertia — the more massive a body, the harder it is to "
                                        "start, stop or turn."
                                    ),
                                    "prerequisites": [],
                                },
                                {
                                    "code": "MOM",
                                    "name": "Linear momentum",
                                    "description": (
                                        "Momentum is mass times velocity: $\\vec p = m\\vec v$. It is a vector "
                                        "with SI unit kg·m/s.\n\nA change in momentum is "
                                        "$\\Delta p = m(v - u)$ — remember the sign when the direction "
                                        "reverses."
                                    ),
                                    "prerequisites": [],
                                },
                                {
                                    "code": "N2",
                                    "name": "Newton's second law (F = ma)",
                                    "description": (
                                        "The net force on a body equals its rate of change of momentum. For "
                                        "constant mass:\n\n$$\\vec F_{net} = m\\vec a$$\n\nThe acceleration "
                                        "points along the **net** force. 1 N is the force that gives 1 kg an "
                                        "acceleration of 1 m/s²."
                                    ),
                                    "prerequisites": ["N1", "MOM", "KIN"],
                                },
                                {
                                    "code": "IMP",
                                    "name": "Impulse",
                                    "description": (
                                        "Impulse is force × the time it acts: $J = F\\,\\Delta t$, and it equals "
                                        "the change in momentum, $J = \\Delta p$.\n\nThe same change in momentum "
                                        "spread over a longer time needs a **smaller force** — why cricketers "
                                        "draw their hands back while catching."
                                    ),
                                    "prerequisites": ["MOM", "N2"],
                                },
                                {
                                    "code": "N3",
                                    "name": "Newton's third law",
                                    "description": (
                                        "When body A exerts a force on body B, B exerts an equal and opposite "
                                        "force on A.\n\nAction and reaction act on **different bodies**, so "
                                        "they never cancel each other."
                                    ),
                                    "prerequisites": ["N1"],
                                },
                            ],
                        },
                        {
                            "name": "Applying the laws of motion",
                            "concepts": [
                                {
                                    "code": "FBD",
                                    "name": "Free-body diagrams",
                                    "description": (
                                        "A free-body diagram isolates one body and shows **only the forces "
                                        "acting on it** (weight, normal force, tension, friction, applied "
                                        "forces) — never the forces it exerts on other bodies."
                                    ),
                                    "prerequisites": ["N2", "N3"],
                                },
                                {
                                    "code": "EQ",
                                    "name": "Equilibrium of a particle",
                                    "description": (
                                        "A particle is in equilibrium when the net force on it is zero: "
                                        "$\\sum \\vec F = 0$. For forces in a plane, the components along each "
                                        "axis must separately add to zero."
                                    ),
                                    "prerequisites": ["FBD"],
                                },
                                {
                                    "code": "FRIC",
                                    "name": "Friction",
                                    "description": (
                                        "**Static friction** adjusts to match the applied force, up to a "
                                        "maximum $f_s^{max} = \\mu_s N$.\n\n**Kinetic friction** acts once "
                                        "surfaces slide: $f_k = \\mu_k N$, opposing the relative motion."
                                    ),
                                    "prerequisites": ["FBD"],
                                },
                                {
                                    "code": "CONN",
                                    "name": "Connected bodies",
                                    "description": (
                                        "For bodies moving together (in contact, or joined by a light string), "
                                        "find the common acceleration from the whole system, then apply "
                                        "$F = ma$ to one body to get the force between them."
                                    ),
                                    "prerequisites": ["N2", "FBD", "FRIC"],
                                },
                                {
                                    "code": "CIRC",
                                    "name": "Dynamics of circular motion",
                                    "description": (
                                        "A body moving in a circle of radius $r$ at speed $v$ needs a net "
                                        "force towards the centre:\n\n$$F_c = \\frac{mv^2}{r}$$\n\nThis "
                                        "centripetal force is supplied by a real force — tension, friction or "
                                        "a component of the normal force."
                                    ),
                                    "prerequisites": ["N2", "KIN"],
                                },
                            ],
                        },
                    ],
                },
            ],
        }
    ],
}


def mcq(code, d, stem, options, correct, solution, hints=(), secs=60):
    ids = "abcdefgh"
    return {
        "concepts": [(code, 1.0)],
        "type": "mcq_single",
        "difficulty": d,
        "stem": stem,
        "content": {"options": [{"id": ids[i], "text": t} for i, t in enumerate(options)]},
        "answer": {"correct": correct},
        "solution": solution,
        "hints": list(hints),
        "estimated_seconds": secs,
    }


def num(code, d, stem, value, unit, solution, hints=(), tol=None, secs=90, extra=()):
    ans = {"value": value}
    if tol is not None:
        ans["tolerance"] = tol
    return {
        "concepts": [(code, 1.0), *extra],
        "type": "numerical",
        "difficulty": d,
        "stem": stem,
        "content": {"unit": unit},
        "answer": ans,
        "solution": solution,
        "hints": list(hints),
        "estimated_seconds": secs,
    }


QUESTIONS = [
    # ── KIN ──
    mcq(
        "KIN",
        1,
        "Acceleration is the rate of change of…",
        ["position", "velocity", "distance", "mass"],
        "b",
        "Acceleration $a = \\Delta v / \\Delta t$ — the rate of change of **velocity**.",
    ),
    num(
        "KIN",
        2,
        "A car starts from rest and reaches 20 m/s in 5 s with uniform acceleration. "
        "What is its acceleration?",
        4,
        "m/s²",
        "$a = \\dfrac{v-u}{t} = \\dfrac{20-0}{5} = 4$ m/s².",
        ["Use $v = u + at$ with $u = 0$."],
        tol=0.01,
    ),
    num(
        "KIN",
        3,
        "A stone is dropped from rest. Taking $g = 10$ m/s², how far does it fall in "
        "the first 3 s?",
        45,
        "m",
        "$s = ut + \\tfrac12 g t^2 = 0 + \\tfrac12(10)(3^2) = 45$ m.",
        ["It starts from rest, so $u = 0$.", "Use $s = ut + \\tfrac12 at^2$."],
        tol=0.1,
    ),
    {
        "concepts": [("KIN", 1.0)],
        "type": "integer",
        "difficulty": 2,
        "stem": "A train moving at 30 m/s brakes with a uniform deceleration of 3 m/s². How many "
        "seconds does it take to stop?",
        "content": {},
        "answer": {"value": 10},
        "solution": "$v = u + at \\Rightarrow 0 = 30 - 3t \\Rightarrow t = 10$ s.",
        "hints": ["Final velocity is 0; acceleration is −3 m/s²."],
        "estimated_seconds": 60,
    },
    # ── N1 ──
    mcq(
        "N1",
        1,
        "When a bus starts suddenly, standing passengers tend to fall backwards. "
        "This is because of…",
        ["inertia of rest", "inertia of motion", "friction from the floor", "Newton's third law"],
        "a",
        "The passengers' bodies tend to stay at rest while the bus moves forward — **inertia "
        "of rest**.",
    ),
    {
        "concepts": [("N1", 1.0)],
        "type": "fill_blank",
        "difficulty": 1,
        "stem": "The tendency of a body to resist any change in its state of rest or uniform "
        "motion is called ___.",
        "content": {"blanks": 1},
        "answer": {"accepted": [["inertia"]]},
        "solution": "This property is **inertia**; mass is its measure.",
        "hints": [],
        "estimated_seconds": 30,
    },
    {
        "concepts": [("N1", 1.0)],
        "type": "assertion_reason",
        "difficulty": 2,
        "stem": "Read the assertion (A) and reason (R) and choose the correct option.",
        "content": {
            "assertion": "A body moving with constant velocity has zero net force on it.",
            "reason": "A body continues in uniform motion unless a net external force acts on it.",
        },
        "answer": {"correct": "a"},
        "solution": "Both are true, and R (Newton's first law) explains A: constant velocity means "
        "zero acceleration, so zero net force.",
        "hints": [],
        "estimated_seconds": 60,
    },
    mcq(
        "N1",
        2,
        "Which of these has the greatest inertia?",
        [
            "a cricket ball (0.16 kg)",
            "a football (0.45 kg)",
            "a shot put (5 kg)",
            "a table-tennis ball (0.003 kg)",
        ],
        "c",
        "Inertia depends only on mass, so the 5 kg shot put has the greatest inertia.",
    ),
    # ── MOM ──
    num(
        "MOM",
        1,
        "What is the momentum of a 2 kg ball moving at 3 m/s?",
        6,
        "kg·m/s",
        "$p = mv = 2 \\times 3 = 6$ kg·m/s.",
        tol=0.01,
        secs=45,
    ),
    mcq(
        "MOM",
        2,
        "What is the SI unit of momentum?",
        ["kg·m/s", "kg·m/s²", "J/m", "N/m"],
        "a",
        "$p = mv$, so its unit is kg × m/s = **kg·m/s** (equivalently N·s).",
    ),
    num(
        "MOM",
        3,
        "A 0.5 kg ball moving at 4 m/s is brought to rest. What is the magnitude of "
        "the change in its momentum?",
        2,
        "kg·m/s",
        "$|\\Delta p| = m|v - u| = 0.5 \\times |0 - 4| = 2$ kg·m/s.",
        tol=0.01,
    ),
    # ── N2 ──
    num(
        "N2",
        1,
        "What net force is needed to give a 5 kg body an acceleration of 2 m/s²?",
        10,
        "N",
        "$F = ma = 5 \\times 2 = 10$ N.",
        tol=0.01,
        secs=45,
    ),
    num(
        "N2",
        2,
        "A 1200 kg car accelerates at 1.5 m/s². What is the net force on it?",
        1800,
        "N",
        "$F = ma = 1200 \\times 1.5 = 1800$ N.",
        tol=1,
    ),
    mcq(
        "N2",
        2,
        "If the net force on a body is doubled and its mass stays the same, its acceleration…",
        ["halves", "doubles", "stays the same", "becomes four times"],
        "b",
        "$a = F/m$: doubling $F$ at constant $m$ doubles $a$.",
    ),
    num(
        "N2",
        3,
        "A 10 kg box is pushed across the floor with a horizontal force of 50 N. The "
        "kinetic friction on it is 20 N. What is its acceleration?",
        3,
        "m/s²",
        "Net force $= 50 - 20 = 30$ N, so $a = 30/10 = 3$ m/s².",
        ["Find the **net** force first."],
        tol=0.01,
        extra=[("FRIC", 0.4)],
    ),
    {
        "concepts": [("N2", 1.0)],
        "type": "mcq_multi",
        "difficulty": 3,
        "stem": "Which statements about $\\vec F = m\\vec a$ are correct? Select all that apply.",
        "content": {
            "options": [
                {"id": "a", "text": "$\\vec F$ is the net external force on the body."},
                {"id": "b", "text": "The acceleration is in the direction of the net force."},
                {"id": "c", "text": "It applies only to bodies at rest."},
                {
                    "id": "d",
                    "text": "For a fixed mass, acceleration is proportional to the net force.",
                },
            ]
        },
        "answer": {"correct": ["a", "b", "d"]},
        "solution": "(a), (b) and (d) are correct. The law applies to moving bodies too — that's "
        "exactly where acceleration happens — so (c) is false.",
        "hints": [],
        "estimated_seconds": 75,
    },
    num(
        "N2",
        4,
        "A lift of mass 500 kg accelerates upwards at 2 m/s². Taking $g = 10$ m/s², "
        "what is the tension in its cable?",
        6000,
        "N",
        "Net upward force $= T - mg = ma$, so $T = m(g + a) = 500 \\times 12 = 6000$ N.",
        [
            "Draw the forces on the lift: tension up, weight down.",
            "Upward acceleration means tension is *greater* than weight.",
        ],
        tol=5,
        secs=120,
        extra=[("FBD", 0.5)],
    ),
    # ── IMP ──
    num(
        "IMP",
        2,
        "A force of 20 N acts on a body for 0.5 s. What impulse does it deliver?",
        10,
        "N·s",
        "$J = F\\Delta t = 20 \\times 0.5 = 10$ N·s.",
        tol=0.01,
        secs=45,
    ),
    mcq(
        "IMP",
        3,
        "A fielder pulls their hands back while catching a fast cricket ball. This…",
        [
            "reduces the impulse on the hands",
            "increases the time of impact, so the force on the hands is smaller",
            "increases the ball's momentum",
            "reduces the change in the ball's momentum",
        ],
        "b",
        "The change in momentum (= impulse) is fixed by the ball. Spreading it over a longer "
        "time reduces the average force $F = \\Delta p / \\Delta t$.",
    ),
    num(
        "IMP",
        4,
        "A 0.15 kg ball moving at 20 m/s is hit straight back at 30 m/s. What is "
        "the magnitude of the impulse on it?",
        7.5,
        "N·s",
        "Taking the return direction as positive: $J = m(v - u) = 0.15\\,(30 - (-20)) = "
        "0.15 \\times 50 = 7.5$ N·s.",
        ["Velocity changes direction — don't just subtract the speeds."],
        tol=0.05,
        secs=120,
        extra=[("MOM", 0.5)],
    ),
    # ── N3 ──
    mcq(
        "N3",
        1,
        "Action and reaction forces…",
        [
            "act on the same body",
            "act on different bodies",
            "cancel each other out",
            "are unequal in size",
        ],
        "b",
        "They are equal and opposite but act on **different** bodies, so they don't cancel.",
    ),
    {
        "concepts": [("N3", 1.0)],
        "type": "assertion_reason",
        "difficulty": 3,
        "stem": "Read the assertion (A) and reason (R) and choose the correct option.",
        "content": {
            "assertion": "Action and reaction forces do not cancel each other.",
            "reason": "Action and reaction act on different bodies.",
        },
        "answer": {"correct": "a"},
        "solution": "Both are true and R explains A: forces only cancel when they act on the same "
        "body.",
        "hints": [],
        "estimated_seconds": 60,
    },
    mcq(
        "N3",
        2,
        "A book rests on a table. What is the reaction to the Earth's gravitational "
        "pull on the book?",
        [
            "the normal force of the table on the book",
            "the force of the book on the table",
            "the gravitational pull of the book on the Earth",
            "friction on the book",
        ],
        "c",
        "The Earth pulls the book, so the reaction is the book pulling the **Earth**. The "
        "normal force is a different interaction (table–book).",
    ),
    # ── FBD ──
    mcq(
        "FBD",
        2,
        "A block rests on a horizontal table. Which forces belong on the block's "
        "free-body diagram?",
        [
            "its weight and the normal force from the table",
            "its weight only",
            "its weight, the normal force, and the force of the block on the table",
            "the normal force only",
        ],
        "a",
        "Only forces **on** the block: its weight (from the Earth) and the normal force (from "
        "the table). The block's push on the table acts on the table.",
    ),
    {
        "concepts": [("FBD", 1.0)],
        "type": "match",
        "difficulty": 3,
        "stem": "Match each force with the body that exerts it.",
        "content": {
            "left": [
                {"id": "l1", "text": "Weight of a book"},
                {"id": "l2", "text": "Normal force on a book lying on a table"},
                {"id": "l3", "text": "Tension on a lamp hanging from a cord"},
                {"id": "l4", "text": "Friction on a box sliding across a floor"},
            ],
            "right": [
                {"id": "r1", "text": "The cord"},
                {"id": "r2", "text": "The Earth"},
                {"id": "r3", "text": "The floor"},
                {"id": "r4", "text": "The table"},
            ],
        },
        "answer": {"pairs": {"l1": "r2", "l2": "r4", "l3": "r1", "l4": "r3"}},
        "solution": "Weight — the Earth; normal force — the table; tension — the cord; friction "
        "— the floor.",
        "hints": [],
        "estimated_seconds": 90,
    },
    # ── EQ ──
    num(
        "EQ",
        2,
        "A 2 kg lamp hangs at rest from a single vertical cord. Taking "
        "$g = 10$ m/s², what is the tension in the cord?",
        20,
        "N",
        "At rest, net force is zero: $T = mg = 2 \\times 10 = 20$ N.",
        tol=0.01,
        secs=45,
    ),
    mcq(
        "EQ",
        3,
        "Three forces act on a particle that is in equilibrium. Their vector sum is…",
        [
            "zero",
            "equal to the largest force",
            "equal to the sum of their magnitudes",
            "directed along the largest force",
        ],
        "a",
        "Equilibrium means zero net force: $\\vec F_1 + \\vec F_2 + \\vec F_3 = 0$.",
    ),
    {
        "concepts": [("EQ", 1.0)],
        "type": "integer",
        "difficulty": 4,
        "stem": "Forces of 3 N and 4 N act on a particle at right angles to each other. What "
        "magnitude (in N) must a third force have to keep the particle in equilibrium?",
        "content": {},
        "answer": {"value": 5},
        "solution": "The third force must cancel the resultant of the first two: "
        "$\\sqrt{3^2 + 4^2} = 5$ N, pointing opposite to it.",
        "hints": ["Find the resultant of the two perpendicular forces."],
        "estimated_seconds": 90,
    },
    # ── FRIC ──
    mcq(
        "FRIC",
        2,
        "A small horizontal push fails to move a heavy box on the floor. The static "
        "friction on the box…",
        [
            "is zero",
            "equals the applied push",
            "always equals $\\mu_s N$",
            "is greater than the applied push",
        ],
        "b",
        "The box isn't accelerating, so static friction exactly balances the push. It only "
        "reaches $\\mu_s N$ when the box is about to slip.",
    ),
    num(
        "FRIC",
        3,
        "A 5 kg block slides on a horizontal floor with coefficient of kinetic "
        "friction 0.2. Taking $g = 10$ m/s², what is the friction force on it?",
        10,
        "N",
        "$N = mg = 50$ N, so $f_k = \\mu_k N = 0.2 \\times 50 = 10$ N.",
        tol=0.01,
    ),
    num(
        "FRIC",
        4,
        "A block slides across a horizontal surface ($\\mu_k = 0.25$) with an "
        "initial speed of 10 m/s. Taking $g = 10$ m/s², how far does it slide before "
        "stopping?",
        20,
        "m",
        "Deceleration $a = \\mu_k g = 2.5$ m/s². From $v^2 = u^2 - 2as$: "
        "$s = \\dfrac{10^2}{2 \\times 2.5} = 20$ m.",
        [
            "Friction is the only horizontal force, so $a = \\mu_k g$.",
            "Use $v^2 = u^2 + 2as$ with $v = 0$.",
        ],
        tol=0.1,
        secs=150,
        extra=[("KIN", 0.5)],
    ),
    {
        "concepts": [("FRIC", 1.0)],
        "type": "fill_blank",
        "difficulty": 2,
        "stem": "Friction that acts between two surfaces sliding over each other is called ___ "
        "friction.",
        "content": {"blanks": 1},
        "answer": {"accepted": [["kinetic", "sliding", "dynamic"]]},
        "solution": "**Kinetic** (sliding) friction, $f_k = \\mu_k N$.",
        "hints": [],
        "estimated_seconds": 30,
    },
    # ── CONN ──
    num(
        "CONN",
        4,
        "Blocks of 2 kg and 3 kg sit side by side on a frictionless floor. A 10 N "
        "horizontal force pushes the 2 kg block, which pushes the 3 kg block. What is their "
        "acceleration?",
        2,
        "m/s²",
        "They move together: $a = \\dfrac{F}{m_1 + m_2} = \\dfrac{10}{5} = 2$ m/s².",
        ["Treat both blocks as one system."],
        tol=0.01,
        secs=120,
    ),
    num(
        "CONN",
        5,
        "In the same set-up (10 N pushing a 2 kg block against a 3 kg block on a "
        "frictionless floor), what force does the 2 kg block exert on the 3 kg block?",
        6,
        "N",
        "The 3 kg block accelerates at 2 m/s² due only to the contact force: "
        "$F = 3 \\times 2 = 6$ N.",
        ["First find the common acceleration.", "Apply $F = ma$ to the 3 kg block alone."],
        tol=0.01,
        secs=150,
    ),
    num(
        "CONN",
        5,
        "Masses of 3 kg and 2 kg hang on either side of a light, frictionless "
        "pulley, joined by a light string. Taking $g = 10$ m/s², what is their acceleration?",
        2,
        "m/s²",
        "$a = \\dfrac{(m_1 - m_2)g}{m_1 + m_2} = \\dfrac{(3 - 2) \\times 10}{5} = 2$ m/s².",
        ["The net driving force is the difference in the weights."],
        tol=0.01,
        secs=150,
    ),
    # ── CIRC ──
    num(
        "CIRC",
        3,
        "A 0.5 kg stone on a string moves in a horizontal circle of radius 2 m at "
        "4 m/s. What centripetal force acts on it?",
        4,
        "N",
        "$F = \\dfrac{mv^2}{r} = \\dfrac{0.5 \\times 4^2}{2} = 4$ N.",
        tol=0.01,
    ),
    mcq(
        "CIRC",
        3,
        "A car takes a turn on a flat (unbanked) road. What provides the centripetal force?",
        [
            "friction between the tyres and the road",
            "the engine",
            "the car's weight",
            "the normal force of the road",
        ],
        "a",
        "On a flat road the only horizontal force on the car is static friction from the road, "
        "which points towards the centre of the turn.",
    ),
    {
        "concepts": [("CIRC", 1.0)],
        "type": "subjective",
        "difficulty": 3,
        "stem": "Explain why roads are often banked on curves.",
        "content": {},
        "answer": {
            "model_answer": (
                "On a banked road, the horizontal component of the normal force points towards the "
                "centre of the curve and supplies (part of) the centripetal force $mv^2/r$. Vehicles "
                "then rely less on friction, so they can take the curve more safely, especially when "
                "the road is wet."
            )
        },
        "solution": "",
        "hints": [],
        "estimated_seconds": 180,
    },
]
