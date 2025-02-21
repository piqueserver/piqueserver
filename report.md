# Report for Assignment 3

This report documents our project details, the onboarding experience, complexity analysis, refactoring plans, and coverage evaluation. The structure follows the provided template, ensuring clarity and consistency across all sections.

---

## Project

**Name:** *[Your Project Name]*  
**URL:** *[Your Project URL]*  

**Description:**  
A concise description of the project in one or two sentences that outlines its primary features and objectives.

---

## Onboarding Experience

The onboarding experience was not completely painless. The documentation is split between a visible `README.md` on GitHub and a separate documentation website, and the instructions on these two sources conflict.

- **Initial Steps:**  
  - We initially followed the instructions on the documentation website to run the code and tests.
  - This approach failed because the dependency requirements did not download as expected.

- **Resolution:**  
  - We then used the recommendations at the bottom of the GitHub page.
  - Once the proper dependencies were downloaded (automatically into a virtual Python environment), the code ran without errors.

- **Dependency Documentation:**  
  - The required dependencies exist in a configuration file but are not explicitly stated in the documentation, leading to some confusion.

---

## Complexity

### Complexity Measurement

We analyzed several complex functions using both manual counts and the Lizard tool. Below is a summary of our findings:

1. **Functions Selected for Analysis:**
   - **Function 1:** `do_move` (lines 48-101 in `./core_commands/movement.py`)
   - **Function 2:** `apply_script.join_squad` (lines 161-223 in `./piqueserver/piqueserver/scripts/squad.py`)
   - **Function 3:** `apply_script.on_spawn` (lines 251-286 in `./piqueserver/scripts/squad.py`)
   - **Function 4:** 

2. **Measurement Results:**
   - **Manual Count:**
     - *First Function:* Adam counted 17,.
     - *Second Function:* Love’s count was 20.
     - *Third Function:* Both Filip and Robin counted 20.
   - **Lizard (Cyclomatic) Complexity:**
     - First function: **19**
     - Second function: **20**
     - Third function: **20**

3. **Observations:**
   - The tool-based and manual methods yielded different results, highlighting that cyclomatic complexity can vary based on the counting method used.
   - In our case, the complex functions are also long. Although there is a correlation between complexity and length, the function’s purpose ultimately guides its design.

4. **Function Purposes:**
   - **`do_move`:**  
     Moves a character within a 3D game environment.
   - **`join_squad`:**  
     Manages the process of a player joining or leaving a squad by performing several checks (e.g., verifying squad capacity, handling transitions between squads, and notifying other players).
   - **`on_spawn`:**  
     Handles player spawning with a focus on squad-based spawning, ensuring players appear near their squad members and updating spawn-related data.

5. **Exceptions and Documentation:**  
   - The measurement methods did not always account for exceptions.
   - Overall, the documentation is clear regarding possible outcomes, though there is room to improve details on edge cases.

---

## Refactoring

**Plan for Refactoring:**  
We plan to refactor the complex functions to reduce their cyclomatic complexity. The aim is to improve maintainability while being mindful of any potential drawbacks, such as performance trade-offs.

- **Estimated Impact:**  
  Reducing complexity (and thus lowering the CC value) is expected to make the code easier to maintain. However, this might introduce other issues 

- **Current Status:**  

---

## Coverage

### Tools

**Using `coverage.py`:**  
We employed the `coverage.py` tool to measure branch coverage across our codebase.

- **Documentation:**  
  The tool is well-documented, though initially it was challenging to interpret the output because it combined branch and line coverage.
- **Integration:**  
  Instead of integrating it into our build environment, we ran it from the command line and generated an HTML report for local review.

**Coverage Results (from `coverage.py`):**
- **First Function:**
  - Branches: **18**
  - Coverage after adding tests: **77.8%**
- **Second Function:**
  - Branches: **24**
  - Coverage after adding tests: **79.2%**
- **Third Function:**
  - Branches: **12**
  - Coverage after adding tests: **94%**

### Our Own Coverage Tool

We also developed a custom coverage tool that works as follows:

- **Implementation:**  
  A Python dictionary is used where branch IDs are keys set to `False` initially. When a branch is executed by the tests, its corresponding value is set to `True`. After test execution, the tool returns the dictionary, indicating which branches were covered.

- **Results from Our Tool:**
  - **First Function (`do_move`):**
    - Branches: **13**
    - Coverage after tests: 10 out of 13 (~77%)
  - **Second Function:**
    - Branches: **16**
    - Coverage after tests: 13 out of 16 (~81%)

### Evaluation

1. **Detail Level:**  
   The measurement is very detailed, as we have inserted branch counters in each decision point.
2. **Limitations:**  
   Our tool is not dynamic and requires manual instrumentation for each function under test.
3. **Consistency:**  
   The results for the second function differ between our tool and `coverage.py`, which indicates the need for further refinement.

---

## Coverage Improvement

- **Requirements for Improved Coverage:**  
  Detailed comments have been added to describe the requirements for enhancing branch coverage.
- **Reports:**
  - [Old Coverage Report](link)
  - [New Coverage Report](link)
- **Test Cases Added:**  
  - Command used to view the patch: `git diff ...`  

---

## Self-assessment: Way of Working

- **Current State:**  
  Our current workflow is assessed according to the Essence standard.
- **Team Assessment:**  
  The self-assessment was conducted unanimously, though there remain minor uncertainties regarding some items.
- **Areas for Improvement:**  
  We identified potential improvements in documentation clarity, test coverage consistency, and overall team coordination.

---

## Overall Experience

- **Main Take-aways:**  
  
- **Learning Outcomes:**  
 
- **Additional Comments:**  

