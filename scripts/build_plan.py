"""Builds docs/data/plan.json from the Notion "Thirty-day plan".

Page numbers are PDF page indices in the local copies under
~/Library/Mobile Documents/com~apple~CloudDocs/MML (not the print pagination
quoted in Notion). Run: python3 scripts/build_plan.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D2L_PAGES = json.loads((ROOT / "scripts" / "d2l_pages.json").read_text())

# ---------------------------------------------------------------- resources
MML_CH = {2: (23, 70, "Linear Algebra"), 3: (76, 102, "Analytic Geometry"), 4: (104, 143, "Matrix Decompositions"),
          5: (145, 176, "Vector Calculus"), 6: (178, 228, "Probability and Distributions"),
          7: (231, 253, "Continuous Optimization"), 8: (257, None, "When Models Meet Data"),
          9: (295, None, "Linear Regression"), 10: (323, None, "PCA"), 11: (354, None, "Gaussian Mixture Models"),
          12: (376, None, "SVM Classification")}
MML_SEC = {"2.1": 25, "2.2": 28, "2.3": 33, "2.4": 41, "2.5": 46, "2.6": 50, "2.7": 54, "3.1": 77, "3.2": 78,
           "3.3": 81, "3.4": 82, "3.5": 84, "3.8": 87, "4.1": 105, "4.2": 111, "4.4": 121, "4.5": 125, "4.6": 135,
           "5.1": 147, "5.2": 152, "5.3": 155, "5.4": 161, "5.5": 164, "5.6": 165, "6.1": 178, "6.2": 184, "6.3": 189,
           "6.4": 192, "6.5": 203, "7.1": 233, "7.3": 242, "9.2": 298, "10.2": 326, "10.4": 339, "11.3": 366,
           "12.2": 380}
D2L_SLUG = {"2.3": "chapter_preliminaries/linear-algebra", "2.4": "chapter_preliminaries/calculus",
            "2.5": "chapter_preliminaries/autograd", "2.6": "chapter_preliminaries/probability",
            "3": "chapter_linear-regression/index", "3.1": "chapter_linear-regression/linear-regression",
            "3.4": "chapter_linear-regression/linear-regression-scratch",
            "3.6": "chapter_linear-regression/generalization", "3.7": "chapter_linear-regression/weight-decay",
            "4": "chapter_linear-classification/index", "4.1": "chapter_linear-classification/softmax-regression",
            "4.4": "chapter_linear-classification/softmax-regression-scratch",
            "4.6": "chapter_linear-classification/generalization-classification",
            "5": "chapter_multilayer-perceptrons/index", "5.1": "chapter_multilayer-perceptrons/mlp",
            "5.3": "chapter_multilayer-perceptrons/backprop",
            "5.4": "chapter_multilayer-perceptrons/numerical-stability-and-init",
            "5.5": "chapter_multilayer-perceptrons/generalization-deep",
            "7": "chapter_convolutional-neural-networks/index", "7.1": "chapter_convolutional-neural-networks/why-conv",
            "7.2": "chapter_convolutional-neural-networks/conv-layer",
            "7.3": "chapter_convolutional-neural-networks/padding-and-strides",
            "7.4": "chapter_convolutional-neural-networks/channels",
            "7.5": "chapter_convolutional-neural-networks/pooling",
            "7.6": "chapter_convolutional-neural-networks/lenet", "8": "chapter_convolutional-modern/index",
            "12": "chapter_optimization/index", "12.3": "chapter_optimization/gd", "12.4": "chapter_optimization/sgd",
            "12.6": "chapter_optimization/momentum", "12.10": "chapter_optimization/adam",
            "12.11": "chapter_optimization/lr-scheduler", "14": "chapter_computer-vision/index",
            "14.2": "chapter_computer-vision/fine-tuning"}
ISLR_CH = {2: (30, 67, "Statistical Learning"), 3: (74, 135, "Linear Regression"), 4: (142, 183, "Classification"),
           5: (190, 212, "Resampling Methods"), 6: (218, 274, "Model Selection & Regularization"),
           10: (388, 428, "Unsupervised Learning")}
TP_CH = {3: (39, "Functions"), 5: (61, "Conditionals and recursion"), 6: (73, "Fruitful functions"),
         7: (85, "Iteration"), 10: (111, "Lists"), 11: (125, "Dictionaries"), 15: (169, "Classes and objects"),
         "B": (223, "Analysis of Algorithms")}
MIT = "https://ocw.mit.edu/courses/18-05-introduction-to-probability-and-statistics-spring-2022"
MIT_PSET = {1: "counting & probability", 2: "conditional probability & Bayes", 3: "independence, discrete RVs, expectation",
            4: "continuous RVs, exponential & normal", 5: "joint distributions, covariance & correlation",
            6: "MLE & least squares", 7: "Bayesian updating", 8: "NHST & p-values", 9: "t-tests",
            10: "confidence intervals", 11: "confidence intervals & bootstrap"}


def book(label, file, page, online, solution=None):
    r = {"kind": "book", "label": label, "file": file, "page": page, "online": online}
    if solution:
        r["solution"] = solution
    return r


def web(label, url, kind="web"):
    return {"kind": kind, "label": label, "url": url}


def mml(ch, sec=None):
    start, ex, title = MML_CH[ch]
    online = "https://mml-book.github.io/book/mml-book.pdf#page={}"
    if sec == "ex":
        sol = f"https://github.com/ilmoi/MML-Book/blob/master/end%20of%20chapter%20exercises/Chapter%20{ch}%20Exercises%20-%20PDF.pdf"
        return book(f"MML Ch {ch} Exercises", "mml-book.pdf", ex, online.format(ex), sol)
    if sec:
        p = MML_SEC[sec]
        return book(f"MML §{sec}", "mml-book.pdf", p, online.format(p))
    return book(f"MML Ch {ch} {title}", "mml-book.pdf", start, online.format(start))


def d2l(sec):
    page, title = D2L_PAGES[sec]
    return book(f"D2L §{sec} {title}", "d2l-en.pdf", page, f"https://d2l.ai/{D2L_SLUG[sec]}.html")


def islr(ch, ex=False):
    start, exp, title = ISLR_CH[ch]
    note = " (= ISLP Ch 12)" if ch == 10 else ""
    if ex:
        return book(f"ISLR Ch {ch} Exercises{note}", "ISLR_First_Printing.pdf", exp, "https://www.statlearning.com/")
    return book(f"ISLR Ch {ch} {title}{note}", "ISLR_First_Printing.pdf", start, "https://www.statlearning.com/")


def tp(ch):
    page, title = TP_CH[ch]
    name = f"Appendix {ch}" if ch == "B" else f"Ch {ch}"
    return book(f"Think Python {name} {title}", "thinkpython2.pdf", page,
                f"https://greenteapress.com/thinkpython2/thinkpython2.pdf#page={page}")


def pset(n):
    f = f"mit18_05_s22_pset{n:02d}"
    return book(f"MIT 18.05 PSet {n} — {MIT_PSET[n]}", f"statprob-problemset/{f}.pdf", 1, f"{MIT}/{f}.pdf",
                f"{MIT}/{f}_sol.pdf")


def mit_exam(name, label):
    f = f"mit18_05_s22_{name}"
    return {"kind": "web", "label": f"MIT 18.05 {label}", "url": f"{MIT}/{f}.pdf", "solution": f"{MIT}/{f}_sol.pdf"}


def video(label, url):
    return web(label, url, "video")


COURSERA_PROB = web("Coursera: Intuitive Introduction to Probability",
                    "https://www.coursera.org/learn/introductiontoprobability", "course")
LC75 = web("LeetCode 75 study plan", "https://leetcode.com/studyplan/leetcode-75/")
ESSENCE_LA = video("3B1B Essence of Linear Algebra",
                   "https://www.youtube.com/playlist?list=PLZHQObOWTQDPD3MizzM2xVFitgF8hE_ab")
ERRORS = {"kind": "app", "label": "Open Error Checks", "url": "#/errors"}
NOTEBOOK = "notebook"

LC_DIFF = {1: "Easy", 217: "Easy", 242: "Easy", 125: "Easy", 206: "Easy", 20: "Easy", 283: "Easy", 49: "Medium",
           238: "Medium", 347: "Medium", 704: "Easy", 35: "Easy", 70: "Easy", 33: "Medium", 1603: "Easy",
           155: "Medium", 15: "Medium", 232: "Easy"}

# category -> default workspace
WS = {"Math": "overleaf", "Probability": "overleaf", "Statistics": "overleaf", "Calculus": "overleaf",
      "Linear algebra": "overleaf", "Math/optimization": "overleaf", "ML": "overleaf", "ML theory": "overleaf",
      "Classification": "overleaf", "Neural networks": "overleaf", "PCA": "overleaf", "Convolution": "overleaf",
      "CNN math": "overleaf", "D2L practice": "overleaf", "Basic image processing": "overleaf", "CV": "overleaf",
      "Representation learning": "overleaf", "Visual geometry": "overleaf", "CV practice": "overleaf",
      "ML/CV sprint": "overleaf", "Formula recall": "overleaf", "Warm-up": "overleaf",
      "LeetCode": "leetcode", "LeetCode diagnostic": "leetcode", "LeetCode/complexity": "leetcode",
      "LeetCode/OOP": "leetcode", "LeetCode/data structures": "leetcode", "LeetCode checkpoint": "leetcode",
      "LeetCode sprint": "leetcode", "Timed LeetCode sprint": "leetcode", "Python/algorithms": NOTEBOOK,
      "Python": NOTEBOOK, "Implementation": NOTEBOOK, "Programming": NOTEBOOK, "Control flow / logic": NOTEBOOK,
      "Algorithms": NOTEBOOK, "Log": "errors", "Error log": "errors", "Mark": "errors", "Marking": "errors",
      "Review": "errors", "Mark/re-solve": "errors", "Plan": "errors", "Cool-down": "errors",
      "Weekly check": "errors", "Re-solve": "overleaf"}


def T(cat, time, text, res=(), ws=None):
    problems = []
    for title, num, url in re.findall(r"\[([^\]#]+?) #(\d+)\]\((https://leetcode\.com/problems/[^)]+)\)", text):
        n = int(num)
        if not any(p["id"] == n for p in problems):
            problems.append({"id": n, "title": title.strip(), "url": url, "difficulty": LC_DIFF.get(n, "")})
    workspace = ws or WS.get(cat) or ("leetcode" if problems else "overleaf")
    return {"cat": cat, "time": time, "text": text, "resources": list(res), "problems": problems,
            "workspace": workspace}


def lc(n, title):
    return f"[{title} #{n}](https://leetcode.com/problems/{SLUG[n]}/)"


SLUG = {1: "two-sum", 217: "contains-duplicate", 242: "valid-anagram", 125: "valid-palindrome",
        206: "reverse-linked-list", 20: "valid-parentheses", 283: "move-zeroes", 49: "group-anagrams",
        238: "product-of-array-except-self", 347: "top-k-frequent-elements", 704: "binary-search",
        35: "search-insert-position", 70: "climbing-stairs", 33: "search-in-rotated-sorted-array",
        1603: "design-parking-system", 155: "min-stack", 15: "3sum", 232: "implement-queue-using-stacks"}

# ---------------------------------------------------------------- the plan
WEEKS = [
    {"n": 1, "title": "Connect math foundations, Python mechanics and regression",
     "goal": "Be able to manipulate vectors/matrices, differentiate simple losses, trace Python control flow and explain linear regression + gradient descent."},
    {"n": 2, "title": "Probability/statistics, algorithmic thinking and classification",
     "goal": "Solve Bayes/expectation/statistics problems, write code using core data structures, analyze basic time complexity and compare regression with classification."},
    {"n": 3, "title": "Gradients, neural networks, PCA, clustering and computer vision",
     "goal": "Derive a gradient update, trace a neural-network forward/backward pass, explain PCA and k-means, calculate convolution output dimensions, and recognize basic CV geometry/representation concepts."},
    {"n": 4, "title": "Consolidation, timed practice and review",
     "goal": "Demonstrate recall under time pressure, avoid repeat errors, and know when to move on rather than over-study one topic."},
]

DAYS = [
 (1, "2026-10-19", "2.5 h", "Baseline diagnostic", [
  T("Math", "45 min", "Closed-book mini-set: 3 matrix/vector questions, 3 derivative/chain-rule questions, 4 probability/statistics questions. Use MML Chapters 2, 5 and 6 if you need questions.",
    [mml(2, "ex"), mml(5, "ex"), mml(6, "ex")]),
  T("LeetCode diagnostic", "35 min", f"Attempt {lc(1, 'Two Sum')}, {lc(217, 'Contains Duplicate')}, and {lc(242, 'Valid Anagram')}. Time-box each attempt; record whether you needed a hint and state the time/space complexity. Prioritize diagnosing gaps over finishing all three."),
  T("ML", "35 min", "Explain without notes: regression vs classification, train/validation/test, loss vs metric, gradient descent, PCA, clustering and neural-network layers. Then solve 5 basic questions from D2L Chapters 3–5.",
    [d2l("3"), d2l("4"), d2l("5")]),
  T("Mark", "20 min", "Label every miss: concept, calculation, careless, or coding. Don't try to repair everything today.", [ERRORS]),
  T("Error log", "15 min", "Rank your 5 highest-priority gaps. These are your repair targets for Week 1.", [ERRORS]),
  T("Repair", "only if needed", "Video, only if needed: Essence of Linear Algebra.", [ESSENCE_LA], ws="none"),
 ]),
 (2, "2026-10-20", "2.5 h", "Vectors, matrices and model outputs", [
  T("Math", "65 min", "MML Chapter 2, especially systems of equations, matrices, matrix-vector products, span/basis/rank. Attempt 4 end-of-chapter exercises; at least one should require solving a linear system.",
    [mml(2, "2.1"), mml(2, "2.2"), mml(2, "2.3"), mml(2, "2.6"), mml(2, "ex")]),
  T("LeetCode", "40 min", f"Solve {lc(1, 'Two Sum')} and {lc(217, 'Contains Duplicate')}. For Two Sum, first write the brute-force O(n²) approach, then improve it with a hash map. Explain why the optimized version changes the time/space trade-off."),
  T("ML", "25 min", "D2L §§3.1–3.4: write the linear-regression prediction equation, MSE loss, and matrix shapes for a batch of examples.",
    [d2l("3.1"), d2l("3.4")]),
  T("Repair", "15 min", "Watch only the linear-algebra video segment needed for the missed questions.", [ESSENCE_LA], ws="none"),
  T("Log", "5 min", "Write the most common shape/algebra mistake.", [ERRORS]),
 ]),
 (3, "2026-10-21", "2.5 h", "Matrix geometry, data structures and regression loss", [
  T("Math", "55 min", "MML Chapter 3: dot products, norms, distances, orthogonality and projections. Do 3 end-of-chapter exercises.",
    [mml(3, "3.1"), mml(3, "3.2"), mml(3, "3.4"), mml(3, "3.8"), mml(3, "ex")]),
  T("LeetCode", "45 min", f"Solve {lc(242, 'Valid Anagram')} and {lc(125, 'Valid Palindrome')}. Compare a sorting-based solution with a frequency-count solution for Anagram; for Palindrome, handle punctuation/case and explain your two-pointer invariant."),
  T("ML", "30 min", "D2L §§3.1, 3.4 and 3.6: calculate predictions and MSE by hand on a tiny dataset; explain overfitting/generalization in your own words.",
    [d2l("3.1"), d2l("3.4"), d2l("3.6")]),
  T("Repair", "15 min", "[StatQuest linear regression](https://www.youtube.com/watch?v=nk2CQITm_eo), only the segment needed.",
    [video("StatQuest — Linear Regression", "https://www.youtube.com/watch?v=nk2CQITm_eo")], ws="none"),
  T("Log", "5 min", "Log today's misses.", [ERRORS]),
 ]),
 (4, "2026-10-22", "2.5 h", "Derivatives, recursion and gradient descent", [
  T("Math", "60 min", "MML Chapter 5: derivatives, partial derivatives, gradients and chain rule. Do 3 end-of-chapter exercises. Include a gradient of a quadratic function.",
    [mml(5, "5.1"), mml(5, "5.2"), mml(5, "5.3"), mml(5, "ex")]),
  T("LeetCode", "40 min", f"Solve {lc(206, 'Reverse Linked List')}. Implement the iterative version first, then the recursive version if time permits. Trace pointer changes on a 3-node list and state the base case for recursion."),
  T("ML", "30 min", "Derive one gradient-descent update for a one-parameter quadratic loss. Explain the direction of the gradient and the effect of a learning rate that is too high.",
    [mml(7, "7.1"), d2l("12.3")]),
  T("Repair", "15 min", "[Essence of Calculus](https://www.youtube.com/playlist?list=PLZHQObOWTQDMsr9K-rj53DwVRMYO3t5Yr) or [Gradient Descent, Step-by-Step](https://www.youtube.com/watch?v=sDv4f4s2SB8).",
    [video("3B1B Essence of Calculus", "https://www.youtube.com/playlist?list=PLZHQObOWTQDMsr9K-rj53DwVRMYO3t5Yr"),
     video("StatQuest — Gradient Descent", "https://www.youtube.com/watch?v=sDv4f4s2SB8")], ws="none"),
  T("Log", "5 min", "Log today's misses.", [ERRORS]),
 ]),
 (5, "2026-10-23", "2.5 h", "Probability basics, logic and ML theory", [
  T("Probability", "55 min", "Coursera Probability course Module 1 (Probability) practice/assignments, or MML Chapter 6. Compute probabilities using unions, intersections and complements; attempt at least 5 questions.",
    [COURSERA_PROB, mml(6, "6.1"), mml(6, "6.2"), mml(6, "6.3"), pset(1)]),
  T("LeetCode", "40 min", f"Solve {lc(20, 'Valid Parentheses')} using a stack, then attempt {lc(283, 'Move Zeroes')} with in-place modification. Before coding, write down the invariant and test empty/minimum-size and repeated-value cases."),
  T("ML theory", "35 min", "D2L §§3.6–3.7: training vs test error, overfitting, weight decay and the reason to keep validation data separate.",
    [d2l("3.6"), d2l("3.7")]),
  T("Repair", "15 min", "[What Is Bayes' Theorem and How Is It Used?](https://www.youtube.com/watch?v=ONCOkccpk3w), if conditional probability is shaky.",
    [video("StatQuest — Bayes' Theorem", "https://www.youtube.com/watch?v=ONCOkccpk3w")], ws="none"),
  T("Log", "5 min", "Log today's misses.", [ERRORS]),
 ]),
 (6, "2026-10-24", "8 h", "Math/Python/regression workshop", [
  T("Math", "2 h", "Redo the missed MML Chapter 2/3/5 exercises. Then solve a fresh set of 6 problems without notes: matrix multiplication, rank/basis, orthogonality/projection, derivatives, partial derivatives and chain rule.",
    [mml(2, "ex"), mml(3, "ex"), mml(5, "ex")]),
  T("LeetCode", "1.5 h", f"Work on {lc(49, 'Group Anagrams')} and {lc(238, 'Product of Array Except Self')}. These are medium-level pattern problems: try each independently for 25–30 minutes before reading hints. If you finish early, attempt {lc(347, 'Top K Frequent Elements')}.", [LC75]),
  T("ML", "1.5 h", "From scratch in NumPy, implement linear regression prediction, MSE, analytical gradient and 20 gradient-descent updates. Compare the loss before and after training.",
    [d2l("3.4"), mml(9, "9.2")], ws=NOTEBOOK),
  T("Timed set", "1.5 h", "12 mixed questions across math, Python and regression. No videos or notes during the set.", ws="overleaf"),
  T("Mark/re-solve", "1 h", "Correct every miss and solve it again from a blank page or file.", [ERRORS]),
  T("Log", "30 min", "Identify patterns. Don't write a long summary; write compact rules and examples.", [ERRORS]),
 ]),
 (7, "2026-10-25", "8 h", "Probability, descriptive statistics and algorithms", [
  T("Probability", "2 h", "MML Chapter 6 end-of-chapter exercises plus 6 MIT OCW probability questions. Cover sample spaces, conditional probability, independence, Bayes' rule and expected value.",
    [mml(6, "ex"), pset(1), pset(2), pset(3)]),
  T("Statistics", "1 h", "Calculate mean, median, variance, standard deviation and covariance by hand on tiny datasets. Explain sample vs population variance.",
    [mml(6, "6.4"), video("StatQuest — Mean, Variance, SD", "https://www.youtube.com/watch?v=SzZ6GpcfoQY")]),
  T("LeetCode/complexity", "1.5 h", f"Solve {lc(704, 'Binary Search')} and {lc(35, 'Search Insert Position')}. Implement iterative binary search, explain the loop invariant, and compare O(log n) search with linear O(n) scanning. Then estimate complexity for one of your Week 1 hash-map solutions.",
    [tp("B")]),
  T("LeetCode", "1 h", "Do a timed retest of two problems you missed earlier in the week, then attempt one unseen easy/medium problem from the LeetCode 75 study plan. Spend the final 10 minutes explaining your approach and complexity without looking at the solution.",
    [LC75], ws="leetcode"),
  T("Weekly mini-test", "1.5 h", "5 math questions, 4 coding/tracing questions and 5 ML questions, closed book.", ws="overleaf"),
  T("Review", "1 h", "Mark; schedule mistakes for Days 8–10.", [ERRORS]),
 ]),
 (8, "2026-10-26", "2.5 h", "Conditional probability and classification", [
  T("Probability", "60 min", "Coursera Probability Module 2 (Conditional Probability) questions 2.1–2.6, or MML Chapter 6. Solve 5 problems with conditional probability, independence and Bayes' rule.",
    [COURSERA_PROB, mml(6, "6.3"), pset(2)]),
  T("LeetCode", "35 min", f"Solve {lc(347, 'Top K Frequent Elements')} or, if it is too difficult today, start with {lc(49, 'Group Anagrams')}. Focus on frequency maps, tuple keys, and why a dictionary is a better fit than repeated nested scans."),
  T("ML", "35 min", "D2L §§4.1–4.4: score vectors, softmax, cross-entropy and the difference between binary and multiclass classification.",
    [d2l("4.1"), d2l("4.4")]),
  T("Repair", "15 min", "[Bayes' theorem video](https://www.youtube.com/watch?v=ONCOkccpk3w).",
    [video("StatQuest — Bayes' Theorem", "https://www.youtube.com/watch?v=ONCOkccpk3w")], ws="none"),
  T("Log", "5 min", "Log today's misses.", [ERRORS]),
 ]),
 (9, "2026-10-27", "2.5 h", "Random variables, recursion and metrics", [
  T("Probability", "55 min", "Coursera modules 4–5 (Discrete Random Variables and Normal Distribution): expected value, variance, binomial and normal distribution. Do at least 5 assignments/questions.",
    [COURSERA_PROB, mml(6, "6.4"), mml(6, "6.5"), pset(3), pset(4)]),
  T("LeetCode", "40 min", f"Solve {lc(70, 'Climbing Stairs')} and explain the recursive recurrence before implementing the efficient solution. Then revisit {lc(206, 'Reverse Linked List')} and write both iterative and recursive versions; compare their auxiliary space.",
    [tp(5)]),
  T("Classification", "35 min", "Compute TP/FP/TN/FN, precision, recall, specificity, accuracy and F1 from 2 tiny confusion matrices. Explain why accuracy can be misleading for imbalanced classes.",
    [islr(4)]),
  T("Repair", "15 min", "[Mean, Variance and Standard Deviation](https://www.youtube.com/watch?v=SzZ6GpcfoQY) or [Normal Distribution](https://www.youtube.com/watch?v=rzFX5NWojp0).",
    [video("StatQuest — Mean, Variance, SD", "https://www.youtube.com/watch?v=SzZ6GpcfoQY"),
     video("StatQuest — Normal Distribution", "https://www.youtube.com/watch?v=rzFX5NWojp0")], ws="none"),
  T("Log", "5 min", "Log today's misses.", [ERRORS]),
 ]),
 (10, "2026-10-28", "2.5 h", "Descriptive statistics, complexity and logistic regression", [
  T("Statistics", "50 min", "MIT 18.05 problem set/questions on distributions and expectation. Calculate mean, variance, covariance and correlation; interpret what each measures.",
    [pset(3), pset(5)]),
  T("LeetCode/complexity", "45 min", f"Solve {lc(704, 'Binary Search')} and attempt {lc(33, 'Search in Rotated Sorted Array')} (medium). Explain when the sorted-half invariant holds and write time/space complexity before checking any editorial."),
  T("Classification", "35 min", "D2L §4.1 / ISLP Chapter 4: sigmoid/logistic regression, decision threshold, log loss and regularization. Calculate probabilities from simple logits.",
    [d2l("4.1"), islr(4), islr(4, ex=True)]),
  T("Repair", "15 min", "[Logistic regression coefficients](https://www.youtube.com/watch?v=vN5cNN2-HWE).",
    [video("StatQuest — Logistic Regression Coefficients", "https://www.youtube.com/watch?v=vN5cNN2-HWE")], ws="none"),
  T("Log", "5 min", "Log today's misses.", [ERRORS]),
 ]),
 (11, "2026-10-29", "2.5 h", "Inference, OOP and generalization", [
  T("Statistics", "50 min", "Selected MIT 18.05 questions on sampling, confidence intervals and hypothesis testing. Know what a p-value/interval means, and what it does not mean.",
    [pset(8), pset(9), pset(10)]),
  T("LeetCode/OOP", "45 min", f"Implement {lc(1603, 'Design Parking System')} as a class, then try {lc(155, 'Min Stack')} as the medium extension. Make constructors, instance state, and method behavior explicit; test repeated operations and empty-stack edge cases.",
    [tp(15)]),
  T("ML theory", "35 min", "ISLP Chapter 5/6 or D2L generalization sections: validation, cross-validation, regularization, bias–variance trade-off and data leakage.",
    [islr(5), islr(6), d2l("3.6"), d2l("4.6")]),
  T("Repair", "15 min", "Use StatQuest's [video index](https://statquest.org/video_index.html) for the exact statistical concept you missed.",
    [web("StatQuest video index", "https://statquest.org/video_index.html")], ws="none"),
  T("Log", "5 min", "Log today's misses.", [ERRORS]),
 ]),
 (12, "2026-10-30", "2.5 h", "Mixed probability/statistics and programming checkpoint", [
  T("Math", "55 min", "8 timed problems across conditional probability, expectation/variance, normal distribution, covariance and basic inference. Use MIT OCW problem sets/exams.",
    [mit_exam("prac_exam01_all", "Practice Exam 1"), pset(5), web("MIT 18.05 exams page", f"{MIT}/resources/exams/")]),
  T("LeetCode checkpoint", "45 min", f"Attempt {lc(1, 'Two Sum')}, {lc(20, 'Valid Parentheses')}, and {lc(70, 'Climbing Stairs')}. Time-box each at 15 minutes, add edge-case tests, and do not use autocomplete or AI hints during the first attempt."),
  T("ML", "30 min", "Compare linear regression, logistic regression, softmax regression and k-nearest neighbors by input/output type, loss/objective, and use case.",
    [d2l("3.1"), d2l("4.1"), islr(2)]),
  T("Repair", "15 min", "Revisit the two lowest-scoring task types.", [ERRORS], ws="none"),
  T("Log", "5 min", "Log today's misses.", [ERRORS]),
 ]),
 (13, "2026-10-31", "8 h", "Probability/statistics and classification practice day", [
  T("Probability", "2 h", "Attempt 8–10 MIT 18.05 problems spanning conditional probability, Bayes' rule, random variables, expectation, normal distribution and independence.",
    [pset(2), pset(3), pset(4)]),
  T("Statistics", "1 h", "Take a practice exam section with no notes; mark with the official solution. Redo every wrong question.",
    [mit_exam("prac_exam02a", "Practice Exam 2a"), mit_exam("prac_exam02b", "Practice Exam 2b")]),
  T("LeetCode/data structures", "1.5 h", f"Attempt {lc(20, 'Valid Parentheses')}, {lc(49, 'Group Anagrams')}, {lc(238, 'Product of Array Except Self')}, and {lc(704, 'Binary Search')}. Time-box each attempt; use the last 15 minutes to explain the data structure choice and Big-O. Treat {lc(15, '3Sum')} as an optional stretch problem."),
  T("Classification", "1.5 h", "From scratch, calculate a logistic-regression probability, cross-entropy for a tiny example, and a confusion matrix with metrics. Explain the decision boundary.",
    [d2l("4.1"), islr(4)]),
  T("Timed mixed set", "1 h", "10 problems in one sitting.", ws="overleaf"),
  T("Review", "1 h", "Mark, re-solve and update the error log.", [ERRORS]),
 ]),
 (14, "2026-11-01", "8 h", "Week 2 checkpoint", [
  T("Closed-book test", "2 h", "6 math/probability questions, 3 timed LeetCode problems (choose one array/hash-map, one stack/recursion, and one search problem from the week), and 6 ML/classification questions. No hints during the timed portion.", ws="overleaf"),
  T("Marking", "1 h", "Classify errors and calculate accuracy by topic, not only overall.", [ERRORS]),
  T("Repair", "2 h", "Work on the three weakest concepts from Weeks 1–2. Use one reference or video per gap.", [ERRORS], ws="overleaf"),
  T("Implementation", "1 h", "Implement a basic classifier pipeline with scikit-learn: split data, fit, predict, calculate metrics. Avoid spending time on dataset setup.",
    [web("scikit-learn: Getting started", "https://scikit-learn.org/stable/getting_started.html")]),
  T("Recall drill", "1 h", "Blank-page formula and definitions test.", ws="overleaf"),
  T("Plan", "1 h", "Choose which existing errors to retest on Days 15–17.", [ERRORS]),
 ]),
 (15, "2026-11-02", "2.5 h", "Gradients and neural-network forward pass", [
  T("Math", "55 min", "MML Chapter 5 or D2L §§2.4–2.5. Compute partial derivatives and a gradient using the chain rule. Practise shapes of vectors/matrices in derivatives.",
    [mml(5, "5.2"), mml(5, "5.3"), mml(5, "5.4"), d2l("2.4"), d2l("2.5")]),
  T("LeetCode", "35 min", f"Retest {lc(70, 'Climbing Stairs')} without notes, then implement {lc(206, 'Reverse Linked List')} recursively if you only solved it iteratively before. Trace the call stack and compare auxiliary space."),
  T("ML", "40 min", "D2L §5.1: perform a tiny MLP forward pass by hand: weighted sum, bias, activation, output and loss.",
    [d2l("5.1")]),
  T("Repair", "15 min", "[What Is a Neural Network?](https://www.youtube.com/watch?v=aircAruvnKk).",
    [video("3B1B — What Is a Neural Network?", "https://www.youtube.com/watch?v=aircAruvnKk")], ws="none"),
  T("Log", "5 min", "Log today's misses.", [ERRORS]),
 ]),
 (16, "2026-11-03", "2.5 h", "Gradient descent and optimization", [
  T("Math/optimization", "55 min", "MML Chapter 7, especially gradient descent and learning-rate behavior; attempt the end-of-chapter exercises.",
    [mml(7, "7.1"), mml(7, "ex")]),
  T("Python", "40 min", "Implement gradient descent on a 1D quadratic using a function that returns the loss and gradient. Test too-small, reasonable and too-large learning rates.",
    [d2l("12.3")]),
  T("ML", "35 min", "D2L §§12.3–12.11: distinguish batch GD, SGD, minibatch SGD, momentum, Adam and learning-rate schedules at a conceptual level.",
    [d2l("12.3"), d2l("12.4"), d2l("12.6"), d2l("12.10"), d2l("12.11")]),
  T("Repair", "15 min", "[Gradient Descent, Step-by-Step](https://www.youtube.com/watch?v=sDv4f4s2SB8) or [3Blue1Brown gradient descent](https://www.youtube.com/watch?v=IHZwWFHWa-w).",
    [video("StatQuest — Gradient Descent", "https://www.youtube.com/watch?v=sDv4f4s2SB8"),
     video("3B1B — Gradient Descent", "https://www.youtube.com/watch?v=IHZwWFHWa-w")], ws="none"),
  T("Log", "5 min", "Log today's misses.", [ERRORS]),
 ]),
 (17, "2026-11-04", "2.5 h", "Backpropagation and network behavior", [
  T("Calculus", "45 min", "Solve 4 chain-rule/partial-derivative problems, including one composition of functions.",
    [mml(5, "5.2"), mml(5, "ex")]),
  T("Neural networks", "55 min", "D2L §§5.1, 5.3 and 5.4. Trace forward propagation and backpropagation through a 2-layer toy network; explain why nonlinear activations matter, and what vanishing gradients/poor initialization mean.",
    [d2l("5.1"), d2l("5.3"), d2l("5.4"), mml(5, "5.6")]),
  T("LeetCode/OOP", "30 min", f"Attempt {lc(232, 'Implement Queue using Stacks')}. Design the class interface first, then implement push, pop, peek, and empty. Explain why the amortized complexity differs from the worst case for an individual operation."),
  T("Repair", "15 min", "[What Is Backpropagation?](https://www.youtube.com/watch?v=Ilg3ggewQ5U) or [Backpropagation Calculus](https://www.youtube.com/watch?v=tIeHLnjs5U8).",
    [video("3B1B — What Is Backpropagation?", "https://www.youtube.com/watch?v=Ilg3ggewQ5U"),
     video("3B1B — Backpropagation Calculus", "https://www.youtube.com/watch?v=tIeHLnjs5U8")], ws="none"),
  T("Log", "5 min", "Log today's misses.", [ERRORS]),
 ]),
 (18, "2026-11-05", "2.5 h", "Eigenvectors, SVD and PCA", [
  T("Linear algebra", "55 min", "MML Chapter 4, focus on eigenvalues/eigenvectors and SVD; do 3 end-of-chapter exercises.",
    [mml(4, "4.2"), mml(4, "4.4"), mml(4, "4.5"), mml(4, "ex")]),
  T("PCA", "45 min", "MML Chapter 10 / ISLP Chapter 12: center data, form a covariance matrix, identify the role of eigenvectors/eigenvalues and explain variance retained after dimensionality reduction.",
    [mml(10), mml(10, "10.2"), islr(10)]),
  T("Python", "30 min", "Use NumPy to compute a covariance matrix and run PCA on a tiny dataset. Check output dimensions and explain the transformed coordinates."),
  T("Repair", "15 min", "[StatQuest PCA, Step-by-Step](https://www.youtube.com/watch?v=FgakZw6K1QQ).",
    [video("StatQuest — PCA", "https://www.youtube.com/watch?v=FgakZw6K1QQ")], ws="none"),
  T("Log", "5 min", "Log today's misses.", [ERRORS]),
 ]),
 (19, "2026-11-06", "2.5 h", "Unsupervised learning and theory", [
  T("ML", "55 min", "ISLP Chapter 12 and MML Chapter 11: clustering, k-means objective, centroid update, Gaussian-mixture intuition, and how unsupervised learning differs from classification.",
    [islr(10), mml(11), mml(11, "11.3")]),
  T("Python/algorithms", "40 min", "Implement one k-means iteration on a tiny 2D dataset or trace one manually. State the runtime bottleneck in terms of samples, clusters and dimensions."),
  T("ML theory", "35 min", "Compare PCA, k-means, GMM, SVM and logistic regression by goal, supervision, assumptions and output.",
    [mml(12), islr(4)]),
  T("Repair", "15 min", "[K-means Clustering](https://www.youtube.com/watch?v=4b5d3muPQmA).",
    [video("StatQuest — K-means", "https://www.youtube.com/watch?v=4b5d3muPQmA")], ws="none"),
  T("Log", "5 min", "Log today's misses.", [ERRORS]),
 ]),
 (20, "2026-11-07", "8 h", "Convolution and CNN foundations", [
  T("Convolution", "1.5 h", "Watch [But What Is a Convolution?](https://www.youtube.com/watch?v=KuXjwB4LzSA) only as needed, then calculate valid convolution values for at least two tiny matrices and kernels by hand.",
    [video("3B1B — But What Is a Convolution?", "https://www.youtube.com/watch?v=KuXjwB4LzSA"), d2l("7.2")]),
  T("CNN math", "1 h", "Solve output-size questions for convolution/pooling with different input size, kernel, stride and padding. Explain channels, feature maps and parameter sharing.",
    [d2l("7.3"), d2l("7.4"), d2l("7.5")]),
  T("D2L practice", "1.5 h", "Work through §§7.1–7.6; attempt several end-of-section exercises, including changes to pooling, convolution window size, output channels and number of layers.",
    [d2l("7.1"), d2l("7.6")]),
  T("Basic image processing", "1 h", "Explain image as a tensor, grayscale vs RGB channels, filters, smoothing, edge detection, padding and downsampling. Connect convolution to image filtering.",
    [d2l("7.2")]),
  T("Implementation", "1.5 h", "Compute a convolution and max-pooling operation manually or with NumPy. Then trace the dimensions through a tiny CNN."),
  T("Timed review", "1 h", "8 questions on neural nets, gradients and CNN dimensions.", ws="overleaf"),
  T("Mark", "30 min", "Fix every shape/output-size error.", [ERRORS]),
 ]),
 (21, "2026-11-08", "8 h", "Representation learning and visual geometry", [
  T("CV", "1.5 h", "Watch CS231n Lecture 5 (CNNs) and Lecture 12 (Visualizing and Understanding) from the [CS231n playlist](https://www.youtube.com/playlist?list=PL3FW7Lu3i5JvHM8ljYj-zLfQRF3EO8sYv), skipping sections you already know.",
    [video("CS231n (2017) playlist", "https://www.youtube.com/playlist?list=PL3FW7Lu3i5JvHM8ljYj-zLfQRF3EO8sYv"),
     web("CS231n schedule & slides", "https://cs231n.stanford.edu/2025/schedule.html")]),
  T("Representation learning", "1 h", "Explain learned features/embeddings, early vs late CNN features, transfer learning, fine-tuning and why a representation can help classification.",
    [d2l("14.2"), d2l("14")]),
  T("Visual geometry", "1.5 h", "Learn the core basics: image coordinates vs world/camera coordinates, pinhole camera model, projection, homography/2D transforms, and what camera calibration estimates. Use the [targeted video search](https://www.youtube.com/results?search_query=computer+vision+pinhole+camera+model+projective+geometry+lecture) only to fill gaps.",
    [video("YouTube: pinhole camera & projective geometry", "https://www.youtube.com/results?search_query=computer+vision+pinhole+camera+model+projective+geometry+lecture")]),
  T("CV practice", "1.5 h", "Answer 8 short questions: convolution/pooling output size, RGB tensor shape, affine vs projective transformation, role of camera intrinsics/extrinsics, transfer learning and representation visualization."),
  T("Mixed set", "1 h", f"5 math + 5 ML/CV questions, plus a 30-minute LeetCode retest: choose two from {lc(49, 'Group Anagrams')}, {lc(238, 'Product of Array Except Self')}, {lc(347, 'Top K Frequent Elements')}, {lc(206, 'Reverse Linked List')}, or {lc(704, 'Binary Search')}. Pick one previously missed and one not yet attempted.", ws="overleaf"),
  T("Review", "1 h", "Mark and add the CV-specific misses to the error log.", [ERRORS]),
  T("Weekly check", "30 min", "Rank weakest topics across the whole syllabus.", [ERRORS]),
 ]),
 (22, "2026-11-09", "2.5 h", "Linear algebra/calculus/probability sweep", [
  T("Math", "70 min", "9 questions: matrix multiplication/rank, eigenvector interpretation, gradient/chain rule, gradient-descent update, conditional probability/Bayes, expectation/variance, normal distribution and covariance.",
    [mml(2, "ex"), mml(4, "ex"), mml(5, "ex"), mml(6, "ex"), pset(5)]),
  T("LeetCode", "35 min", f"Choose two previously attempted problems from {lc(242, 'Valid Anagram')}, {lc(20, 'Valid Parentheses')}, {lc(206, 'Reverse Linked List')}, and {lc(704, 'Binary Search')}. Re-solve from a blank editor, then state the invariant and time/space complexity."),
  T("ML", "25 min", "Explain what matrix operations and gradients are doing in linear regression, PCA and an MLP.",
    [mml(9), mml(10), d2l("5.1")]),
  T("Repair", "15 min", "Use MML or the matching Coursera module only for missed principles.", [COURSERA_PROB], ws="none"),
  T("Log", "5 min", "Log today's misses.", [ERRORS]),
 ]),
 (23, "2026-11-10", "2.5 h", "Regression/classification and evaluation", [
  T("ML", "60 min", "8 questions on linear regression, logistic/softmax classification, loss functions, regularization, overfitting, cross-validation and metric choice.",
    [islr(3, ex=True), islr(4, ex=True), islr(5, ex=True)]),
  T("Python", "40 min", "Implement a small train/validation split and compute a confusion matrix, precision, recall and F1 from predictions."),
  T("Math", "30 min", "Compute MSE, sigmoid/softmax probabilities, cross-entropy for a tiny example and a one-step parameter update.",
    [d2l("3.1"), d2l("4.1")]),
  T("Repair", "15 min", "Use StatQuest or D2L only for missed concepts.",
    [web("StatQuest video index", "https://statquest.org/video_index.html")], ws="none"),
  T("Log", "5 min", "Log today's misses.", [ERRORS]),
 ]),
 (24, "2026-11-11", "2.5 h", "Neural networks, backprop and optimization", [
  T("Math", "50 min", "Chain rule and derivative questions, including a simple computational graph.",
    [d2l("5.3"), mml(5, "5.6")]),
  T("ML", "55 min", "Forward pass, loss, backprop direction, activation functions, learning rate, SGD vs Adam, regularization and initialization. Do not aim to prove advanced results; aim for correct reasoning and calculations.",
    [d2l("5.1"), d2l("5.4"), d2l("12.10")]),
  T("Programming", "25 min", "Debug a deliberately flawed gradient-descent loop (wrong sign, wrong update order or mismatched shapes)."),
  T("Repair", "15 min", "Replay only the needed portion of 3Blue1Brown/D2L.",
    [video("3B1B — Backpropagation Calculus", "https://www.youtube.com/watch?v=tIeHLnjs5U8")], ws="none"),
  T("Log", "5 min", "Log today's misses.", [ERRORS]),
 ]),
 (25, "2026-11-12", "2.5 h", "PCA/clustering/CNN/CV sweep", [
  T("Math", "35 min", "Explain eigenvectors/SVD in PCA and calculate a basic convolution output dimension.",
    [mml(4, "4.5"), mml(10, "10.4"), d2l("7.3")]),
  T("ML", "55 min", "Compare PCA, k-means, GMM, SVM, neural networks and CNNs. State purpose, inputs, core assumptions/objective and common failure modes.",
    [mml(10), mml(11), mml(12), d2l("7")]),
  T("CV", "35 min", "Review basic image processing, learned representations, camera projection and homography at a definition/application level.",
    [d2l("14.2")]),
  T("Practice", "20 min", "Solve 5 short mixed questions.", ws="overleaf"),
  T("Repair", "15 min", "Target the weakest one of these concepts.", [ERRORS], ws="none"),
  T("Log", "5 min", "Log today's misses.", [ERRORS]),
 ]),
 (26, "2026-11-13", "2.5 h", "Programming sprint", [
  T("Timed LeetCode sprint", "70 min", f"Solve 3–4 problems without help, selecting from {lc(347, 'Top K Frequent Elements')} (hash map/heap), {lc(15, '3Sum')} (sorting/two pointers), {lc(206, 'Reverse Linked List')} (iteration/recursion), and {lc(155, 'Min Stack')} (class/state/stack). Aim for one easy warm-up and two mediums; if stuck for 20 minutes, take one hint, close it, and finish independently."),
  T("Control flow / logic", "30 min", "Trace conditionals, boolean precedence, loops, early returns and edge cases.",
    [tp(5), tp(7)]),
  T("Algorithms", "25 min", "State time complexity and explain why for each solution.", [tp("B")]),
  T("Repair", "20 min", "Read only the relevant LeetCode hint/editorial section for a repeated pattern, close it, and re-solve the problem from scratch. Look up Python syntax only when it blocks implementation.", ws="leetcode"),
  T("Log", "5 min", "Log today's misses.", [ERRORS]),
 ]),
 (27, "2026-11-14", "9 h", "Mock exam 1", [
  T("Mock", "3 h", "Closed-book, no AI, no videos, no notes. Suggested split: 60 min math; 60 min programming/algorithms using 2–3 unseen or previously missed LeetCode problems (mix one easy with medium-level array/hash-map, stack, recursion, linked-list, or binary-search patterns); 60 min ML. Include 20–30 min of CV questions inside the ML block.",
    [mit_exam("prac_exam_final", "Practice Final")], ws="overleaf"),
  T("Break", "30 min", "Step away from the screen.", ws="none"),
  T("Mark", "1.5 h", "Use solutions/resources only after attempting every question. Mark wrong answers and lucky guesses separately.", [ERRORS]),
  T("Repair", "2 h", "Select the 3 weakest subtopics and do new questions, not just reread explanations.", [ERRORS], ws="overleaf"),
  T("Re-solve", "1 h", "Redo missed questions from a blank page/file."),
  T("Log", "30 min", "Rank errors by severity and likelihood of appearing again.", [ERRORS]),
  T("Cool-down", "30 min", "Summarize only the 5 highest-yield corrections.", [ERRORS]),
 ]),
 (28, "2026-11-15", "8 h", "Mock exam 2 and error repair", [
  T("Mock", "2.5–3 h", "A second mixed set with different questions. Make it slightly harder by including a few derivation and edge-case questions.",
    [mit_exam("exam_final", "Final Exam")], ws="overleaf"),
  T("Mark", "1.5 h", "Calculate topic-level accuracy and identify repeated errors.", [ERRORS]),
  T("Repair", "2 h", "If an error repeats, go back to a short reference section and then solve 2 similar problems. Don't rewatch an entire playlist.", [ERRORS], ws="overleaf"),
  T("LeetCode sprint", "45 min", f"Redo one hash-map problem ({lc(347, 'Top K Frequent Elements')} or {lc(49, 'Group Anagrams')}), one recursion/linked-list problem ({lc(206, 'Reverse Linked List')}), and one binary-search problem ({lc(35, 'Search Insert Position')}). Prioritize problems you previously missed."),
  T("ML/CV sprint", "45 min", "Redo a gradient/MLP problem, one PCA/clustering problem and one CNN/geometry question."),
  T("Formula recall", "30 min", "Write key equations and definitions from memory."),
 ]),
 (29, "2026-11-16", "2.5 h", "Repair only the top weaknesses", [
  T("Weak area 1", "45 min", "Solve 3 fresh questions.", [ERRORS], ws="overleaf"),
  T("Weak area 2", "45 min", "Solve 3 fresh questions.", [ERRORS], ws="overleaf"),
  T("Weak area 3", "35 min", "Solve 2 fresh questions or one coding problem.", [ERRORS], ws="overleaf"),
  T("Formula/logic sheet", "20 min", "Consolidate formulas, common Python traps, algorithm complexities and ML comparisons.", ws="overleaf"),
  T("Log", "5 min", "Decide what not to study again unless it appears on the error list.", [ERRORS]),
 ]),
 (30, "2026-11-17", "2–2.5 h", "Final light review", [
  T("Warm-up", "30 min", "Closed-book recall: matrix operations, derivatives/chain rule, Bayes, expectation/variance, gradient descent, loss functions, classification metrics, PCA, k-means and CNN dimensions."),
  T("Mini-test", "45 min", "12 mixed questions under time pressure. Stop when time expires.", ws="overleaf"),
  T("Mark", "25 min", "Review only the misses and any lucky guesses.", [ERRORS]),
  T("LeetCode", "20 min", "Re-solve one previously missed easy problem without notes, then explain its edge cases and time/space complexity aloud. Do not start a new problem today.", ws="leetcode"),
  T("Final review", "10 min", "Review the formula sheet and error log. No new topic and no long video today.", [ERRORS], ws="errors"),
 ]),
]


def main():
    days = []
    for n, date, hours, title, tasks in DAYS:
        week = (n - 1) // 7 + 1 if n <= 28 else 4
        for i, t in enumerate(tasks):
            t["id"] = f"d{n}t{i + 1}"
        days.append({"n": n, "date": date, "hours": hours, "title": title, "week": week, "tasks": tasks})
    plan = {"title": "MML30 — 30-day MML learning plan", "start": "2026-10-19", "end": "2026-11-17",
            "overleaf": "https://www.overleaf.com/project/6adaca2e9783ef342efceec6",
            "weeks": WEEKS, "days": days}
    out = ROOT / "docs" / "data" / "plan.json"
    out.write_text(json.dumps(plan, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {out} ({len(days)} days, {sum(len(d['tasks']) for d in days)} tasks)")


if __name__ == "__main__":
    main()
