# Circuit Design GUI - User Roles & Permissions

## Understanding Roles vs Personas

**Personas** = Who they are (Alex, Dr. Martinez, Dr. Patel)  
**Roles** = What permissions/capabilities they have in the system

*One persona may use multiple roles. For example, Dr. Patel might be both a Researcher AND an Instructor.*

---

## Role Definitions

### 1. Student Role

**Who uses this:** Primarily Alex (undergrads), also grad students in coursework mode

**Core Purpose:** Learn circuits through guided design and simulation

**Key Capabilities:**
- ✅ Create and edit personal circuit designs
- ✅ Run simulations on own circuits
- ✅ Save/load personal project files
- ✅ Access shared example library (read-only)
- ✅ Submit assignments (if connected to LMS)
- ✅ View own simulation history and results
- ✅ Export circuits (PDF, images, netlist)
- ✅ Access tutorials and help documentation

**Restrictions:**
- ❌ Cannot modify shared example library
- ❌ Cannot access other students' work
- ❌ Cannot create assignments or templates
- ❌ Cannot view class-wide analytics
- ❌ Limited to standard component library (unless instructor grants access)
- ❌ May have simulation complexity limits (optional, for performance)

**Interface Defaults:**
- Beginner mode enabled by default
- Extensive tooltips and contextual help
- Guided workflows for common tasks
- Simplified error messages

---

### 2. Instructor Role

**Who uses this:** Dr. Martinez (course instructors), TAs with elevated permissions

**Core Purpose:** Create learning experiences, manage student work, assess progress

**Key Capabilities:**
- ✅ All Student role capabilities
- ✅ Create and publish assignment templates
- ✅ Access/view student submissions (within their course)
- ✅ Grade and provide feedback on student work
- ✅ Create and manage shared example circuits
- ✅ Configure assignment parameters (due dates, allowed components, etc.)
- ✅ View class-wide analytics and progress
- ✅ Bulk operations (distribute files, collect submissions)
- ✅ Create custom component libraries for specific courses
- ✅ Set up verification criteria for auto-grading
- ✅ Export class data and reports
- ✅ Manage course roster (add/remove students)
- ✅ Lock/unlock assignment files
- ✅ Create read-only demonstration circuits

**Restrictions:**
- ❌ Cannot access students from other instructors' courses
- ❌ Cannot modify global system settings
- ❌ Cannot access advanced research features (unless also Researcher role)
- ❌ Cannot manage user accounts (system-wide)

**Interface Features:**
- Course management dashboard
- Student progress tracking
- Assignment creation wizard
- Bulk verification tools
- Analytics and reporting

---

### 3. Researcher Role

**Who uses this:** Dr. Patel (grad researchers, faculty), advanced users doing original work

**Core Purpose:** Conduct novel circuit research and development

**Key Capabilities:**
- ✅ All Student role capabilities
- ✅ Access to advanced simulation controls
  - Custom solver settings
  - Convergence parameters
  - Multi-threading options
- ✅ Import custom SPICE models
- ✅ Create custom subcircuits and components
- ✅ Scripting/API access (Python, MATLAB integration)
- ✅ Batch simulation and parameter sweeps
- ✅ Monte Carlo and optimization runs
- ✅ Access to full component model library
- ✅ Advanced data export (raw data, custom formats)
- ✅ Performance profiling tools
- ✅ Integration with version control systems
- ✅ Collaboration tools (shared workspaces)
- ✅ Remove artificial complexity limits

**Restrictions:**
- ❌ Cannot access other researchers' private projects (unless shared)
- ❌ Cannot manage courses or students (unless also Instructor role)

**Interface Features:**
- Advanced mode with full feature access
- Scripting console
- Performance monitoring
- Detailed simulation logs
- Professional export options

---

### 4. Teaching Assistant (TA) Role

**Who uses this:** Graduate TAs, undergraduate course assistants

**Core Purpose:** Support students and assist instructor with course management

**Key Capabilities:**
- ✅ All Student role capabilities
- ✅ View student work (within assigned course)
- ✅ Provide feedback and comments on student circuits
- ✅ Answer student questions about their designs
- ✅ Access shared examples and assignment templates
- ✅ View course analytics
- ✅ Help with technical troubleshooting

**Restrictions:**
- ❌ Cannot create or modify assignments (instructor-only)
- ❌ Cannot change grades (can recommend, instructor approves)
- ❌ Cannot modify course roster
- ❌ Cannot access instructor administrative tools
- ❌ Limited to courses they're assigned to

**Interface Features:**
- Student support view
- Queue/ticket system for help requests
- Read-only access to assignment solutions
- Annotation tools for providing feedback

---

### 5. Administrator Role

**Who uses this:** IT staff, system administrators

**Core Purpose:** Manage the system, users, and global settings

**Key Capabilities:**
- ✅ Manage all user accounts
- ✅ Assign and modify user roles
- ✅ Configure system-wide settings
- ✅ Manage global component libraries
- ✅ Monitor system performance and usage
- ✅ Access all content (for support purposes)
- ✅ Backup and restore operations
- ✅ License management (if applicable)
- ✅ Configure authentication/SSO
- ✅ Generate system-wide reports

**Restrictions:**
- ❌ Should not routinely access student/researcher work (privacy)
- ❌ Does not necessarily have circuit design expertise

**Interface Features:**
- Administrative dashboard
- User management console
- System configuration panels
- Usage monitoring and analytics
- Audit logs

---

## Role Combinations

Users can have multiple roles simultaneously:

### Common Combinations:

**Graduate Student Researcher**
- Student role (for coursework)
- Researcher role (for thesis work)
- Possibly TA role (if teaching assistant)

**Faculty Member**
- Instructor role (for teaching)
- Researcher role (for research projects)

**Advanced Undergraduate**
- Student role (default)
- TA role (if course assistant)

---

## Role Assignment & Transitions

### How Roles Are Assigned

**Student Role:**
- Default for all new academic users
- Auto-assigned via LMS integration or registration
- Persists throughout academic career

**Instructor Role:**
- Assigned by Administrator
- Requires verification of faculty/staff status
- Typically tied to specific courses

**Researcher Role:**
- Requested by user, approved by Administrator
- Graduate students typically granted upon request
- Faculty automatically eligible

**TA Role:**
- Assigned by Instructor for specific courses
- Time-limited (semester/term)
- Removed when TA assignment ends

**Administrator Role:**
- Assigned by existing Administrator
- Typically IT staff or system owners
- Requires institutional authorization

### Self-Service Options

**Students can:**
- Request Researcher role upgrade (with justification)
- View their current role(s)

**Instructors can:**
- Assign TA roles within their courses
- Cannot self-assign Administrator

**Researchers can:**
- Request Instructor role (if teaching)

---

## Permission Matrix

| Capability | Student | TA | Instructor | Researcher | Admin |
|------------|---------|----|-----------|-----------:|-------|
| Create personal circuits | ✅ | ✅ | ✅ | ✅ | ✅ |
| Run simulations | ✅ | ✅ | ✅ | ✅ | ✅ |
| Access examples | ✅ | ✅ | ✅ | ✅ | ✅ |
| View other students' work | ❌ | ✅ | ✅ | ❌ | ✅ |
| Create assignments | ❌ | ❌ | ✅ | ❌ | ✅ |
| Grade submissions | ❌ | 📝* | ✅ | ❌ | ✅ |
| Access advanced features | ❌ | ❌ | ❌ | ✅ | ✅ |
| Use scripting/API | ❌ | ❌ | ❌ | ✅ | ✅ |
| Import custom models | ❌ | ❌ | ⚠️** | ✅ | ✅ |
| Manage course roster | ❌ | ❌ | ✅ | ❌ | ✅ |
| System configuration | ❌ | ❌ | ❌ | ❌ | ✅ |
| User management | ❌ | ❌ | ⚠️*** | ❌ | ✅ |

*📝 TA can recommend grades, instructor approves*  
*⚠️** Instructor can for their specific course*  
*⚠️*** Instructor can only manage students in their course*

---

## Implementation Considerations

### Authentication & Authorization

**Single Sign-On (SSO):**
- Integrate with university authentication (LDAP, Shibboleth, SAML)
- Roles can be mapped from institutional directory

**Role Checking:**
- Check permissions server-side (never trust client)
- Cache role information for performance
- Re-validate on sensitive operations

**Session Management:**
- Role changes take effect on next login
- Support role switching (if user has multiple roles)
- Log role-based actions for audit

### UI/UX Based on Role

**Dynamic Interface:**
- Show/hide features based on active role
- Student sees simplified interface
- Researcher sees advanced controls
- Instructor sees course management tools

**Role Indicator:**
- Display current active role
- Allow switching if user has multiple roles
- Clear visual distinction between modes

**Contextual Help:**
- Help content tailored to current role
- Different documentation for different roles

### Security Considerations

**Data Access:**
- Students cannot access each other's work
- Instructors isolated to their courses
- Researchers' work is private by default
- Admin access logged for privacy compliance

**FERPA Compliance (if US-based):**
- Student data protection
- Grade confidentiality
- Audit trails for access

**Collaboration Features:**
- Explicit sharing required
- Granular permissions (view, comment, edit)
- Revocable access

---

## Example User Journeys

### Journey 1: Alex (Student) → Advanced Student
1. **Start:** Student role, beginner mode
2. **Grows:** Completes intro courses, becomes comfortable
3. **Transition:** Requests Researcher role for senior project
4. **Result:** Gains access to advanced features for thesis work

### Journey 2: Dr. Patel (Grad Student → Faculty)
1. **Start:** Student + Researcher roles (dissertation work)
2. **Adds:** TA role (teaching assistantship)
3. **Transition:** Graduates, hired as faculty
4. **Result:** Instructor + Researcher roles (teaching + research)

### Journey 3: Dr. Martinez (New Instructor)
1. **Start:** Assigned Instructor role
2. **Uses:** Creates first course, assigns TAs
3. **Grows:** Requests Researcher role for summer research project
4. **Result:** Instructor + Researcher (teaching + research)