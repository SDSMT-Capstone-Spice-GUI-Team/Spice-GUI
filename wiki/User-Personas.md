# User Personas

SDM Spice is designed to serve three primary user types: students, instructors, and researchers.

## Alex Chen - Undergraduate Student

### Profile

| Attribute | Value |
|-----------|-------|
| **Age** | 20 |
| **Year** | Junior |
| **Major** | Electrical Engineering |
| **Technical Level** | Intermediate |
| **Primary Device** | Laptop (Windows) |

### Context
Alex is a junior EE student taking Circuits II. They completed the prerequisites but still feel uncertain about circuit analysis. They have experience with basic tools like MATLAB and Excel, but limited exposure to SPICE simulators.

### Goals
- Complete lab assignments accurately and on time
- Build intuition for how circuits behave
- Verify hand calculations with simulation
- Learn without fighting the software

### Pain Points
- Traditional SPICE tools are intimidating and command-line heavy
- Error messages are cryptic and unhelpful
- Hard to know if the circuit is set up correctly
- Limited time to learn complex new tools

### What Alex Needs from SDM Spice
- Intuitive drag-and-drop interface
- Clear, educational error messages
- Visual feedback showing circuit state
- Quick path from design to simulation results
- Examples and tutorials

### Quote
> "I just want to check if my voltage divider calculation is right without spending an hour learning command syntax."

---

## Dr. Maria Martinez - Instructor

### Profile

| Attribute | Value |
|-----------|-------|
| **Age** | 45 |
| **Role** | Associate Professor |
| **Department** | Electrical Engineering |
| **Technical Level** | Expert |
| **Courses** | Circuits I, Circuits II, Electronics |

### Context
Dr. Martinez has taught circuits courses for 15 years. She's comfortable with professional SPICE tools but frustrated by the learning curve they impose on students. She wants students to focus on circuit concepts, not software mechanics.

### Goals
- Reduce time students spend fighting tools
- Create consistent, gradable assignments
- Track student progress across the class
- Focus class time on concepts, not software tutorials

### Pain Points
- Grading 60+ circuit simulations manually
- Students submitting incompatible file formats
- Can't easily see common mistakes across the class
- Setup time for new assignments is significant

### What Dr. Martinez Needs from SDM Spice
- Simple assignment creation workflow
- Automatic submission collection
- Quick visual review of student work
- Analytics showing common errors
- Grade export for the LMS

### Quote
> "I want my students to think about Kirchhoff's laws, not about where to find the ground symbol in a menu."

---

## Dr. Raj Patel - Researcher

### Profile

| Attribute | Value |
|-----------|-------|
| **Age** | 35 |
| **Role** | Research Faculty |
| **Department** | Electrical Engineering |
| **Technical Level** | Expert |
| **Focus** | Power electronics, novel converter topologies |

### Context
Dr. Patel designs advanced power electronics circuits for his research. He's an expert with professional SPICE tools but appreciates efficient interfaces. He sometimes needs to run many simulations with varying parameters.

### Goals
- Quickly prototype circuit ideas
- Run parameter sweeps efficiently
- Use custom component models
- Automate repetitive simulation tasks
- Generate publication-quality plots

### Pain Points
- Professional tools are expensive for student licenses
- Overkill features for quick prototyping
- Want scripting without heavy setup
- Cross-platform support often lacking

### What Dr. Patel Needs from SDM Spice
- Advanced simulation controls
- Custom SPICE model import
- Scripting API for automation
- Batch simulation capability
- High-quality data export

### Quote
> "I need to sweep three parameters across a hundred combinations. Don't make me click through a GUI a hundred times."

---

## Design Implications

### Progressive Disclosure

SDM Spice uses progressive disclosure to serve all three personas:

| Feature | Student View | Instructor View | Researcher View |
|---------|--------------|-----------------|-----------------|
| Simulation Controls | Basic | Basic | Advanced |
| Error Messages | Educational | Educational | Technical |
| Component Library | Common | Common | Expanded |
| Scripting | Hidden | Hidden | Available |
| Analytics | Personal only | Class-wide | Personal |

### Interface Modes

- **Standard Mode**: Optimized for students and basic use
- **Advanced Mode** (Planned): Exposes researcher features

### Error Message Strategy

| User | Message Style | Example |
|------|---------------|---------|
| Student | Educational | "Your circuit needs a ground connection. Every circuit needs a reference point (0V)." |
| Researcher | Technical | "Node 47 floating - no DC path to ground" |

---

## Persona-Based User Stories

### Student Stories
- As a student, I want to drag components onto a canvas so that I can build circuits visually
- As a student, I want clear error messages so that I can fix my circuit without frustration
- As a student, I want to see node voltages on the schematic so that I can verify my calculations

### Instructor Stories
- As an instructor, I want to create assignment templates so that students start with consistent setups
- As an instructor, I want to see all student submissions in one place so that I can grade efficiently
- As an instructor, I want to identify common errors so that I can address them in class

### Researcher Stories
- As a researcher, I want to import custom SPICE models so that I can simulate novel devices
- As a researcher, I want to script parameter sweeps so that I can automate experiments
- As a researcher, I want to export raw data so that I can process it with my own tools

---

## See Also

- [[Project Scope]] - What SDM Spice will include
- [[Roadmap]] - When features will be delivered
- [[Architecture Overview]] - How it's built
