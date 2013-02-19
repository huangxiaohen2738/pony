import unittest
from datetime import date, datetime
from pony.orm.core import *
from pony.orm.sqltranslation import IncomparableTypesError
from testutils import *

db = TestDatabase('sqlite', ':memory:')

class Department(db.Entity):
    number = PrimaryKey(int, auto=True)
    name = Unique(unicode)
    groups = Set("Group")
    courses = Set("Course")

class Group(db.Entity):
    number = PrimaryKey(int)
    major = Required(unicode)
    dept = Required("Department")
    students = Set("Student")

class Course(db.Entity):
    name = Required(unicode)
    semester = Required(int)
    lect_hours = Required(int)
    lab_hours = Required(int)
    credits = Required(int)
    dept = Required(Department)
    students = Set("Student")
    PrimaryKey(name, semester)
    
class Student(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(unicode)
    dob = Required(date)
    tel = Optional(str)
    picture = Optional(buffer, lazy=True)
    gpa = Required(float, default=0)
    group = Required(Group)
    courses = Set(Course)

@with_transaction
def populate_db():
    d1 = Department(name="Department of Computer Science")
    d2 = Department(name="Department of Mathematical Sciences")
    d3 = Department(name="Department of Applied Physics")

    c1 = Course(name="Web Design", semester=1, dept=d1,
                       lect_hours=30, lab_hours=30, credits=3)
    c2 = Course(name="Data Structures and Algorithms", semester=3, dept=d1,
                       lect_hours=40, lab_hours=20, credits=4)

    c3 = Course(name="Linear Algebra", semester=1, dept=d2,
                       lect_hours=30, lab_hours=30, credits=4)
    c4 = Course(name="Statistical Methods", semester=2, dept=d2,
                       lect_hours=50, lab_hours=25, credits=5)

    c5 = Course(name="Thermodynamics", semester=2, dept=d3,
                       lect_hours=25, lab_hours=40, credits=4)
    c6 = Course(name="Quantum Mechanics", semester=3, dept=d3,
                       lect_hours=40, lab_hours=30, credits=5)

    g101 = Group(number=101, major='B.E. in Computer Engineering', dept=d1)
    g102 = Group(number=102, major='B.S./M.S. in Computer Science', dept=d2)
    g103 = Group(number=103, major='B.S. in Applied Mathematics and Statistics', dept=d2)
    g104 = Group(number=104, major='B.S./M.S. in Pure Mathematics', dept=d2)
    g105 = Group(number=105, major='B.E in Electronics', dept=d3)
    g106 = Group(number=106, major='B.S./M.S. in Nuclear Engineering', dept=d3)

    s1 = Student(name='John Smith', dob=date(1991, 3, 20), tel='123-456', gpa=3, group=g101,
                        courses=[c1, c2, c4, c6])
    s1 = Student(name='Matthew Reed', dob=date(1990, 11, 26), gpa=3.5, group=g101,
                        courses=[c1, c3, c4, c5])
    s1 = Student(name='Chuan Qin', dob=date(1989, 2, 5), gpa=4, group=g101,
                        courses=[c3, c5, c6])
    s1 = Student(name='Rebecca Lawson', dob=date(1990, 4, 18), tel='234-567', gpa=3.3, group=g102,
                        courses=[c1, c4, c5, c6])
    s1 = Student(name='Maria Ionescu', dob=date(1991, 4, 23), gpa=3.9, group=g102,
                        courses=[c1, c2, c4, c6])
    s1 = Student(name='Oliver Blakey', dob=date(1990, 9, 8), gpa=3.1, group=g102,
                        courses=[c1, c2, c5])
    s1 = Student(name='Jing Xia', dob=date(1988, 12, 30), gpa=3.2, group=g102,
                        courses=[c1, c3, c5, c6])

db.generate_mapping(create_tables=True)
populate_db()

class TestSQLTranslator2(unittest.TestCase):
    def setUp(self):
        rollback()
    def tearDown(self):
        rollback()
    def test_distinct1(self):
        q = select(c.students for c in Course)
        self.assertEquals(q._translator.distinct, True)
        self.assertEquals(q.count(), 7)
    def test_distinct3(self):
        q = select(d for d in Department if len(s for c in d.courses for s in c.students) > len(s for s in Student))
        self.assertEquals("DISTINCT" in flatten(q._translator.conditions), True)
        self.assertEquals(q[:], [])
    def test_distinct4(self):
        q = select(d for d in Department if len(d.groups.students) > 3)
        self.assertEquals("DISTINCT" not in flatten(q._translator.conditions), True)
        self.assertEquals(q[:], [Department[2]])
    def test_distinct5(self):
        result = select(s for s in Student)[:]
        self.assertEquals(result, [Student[1], Student[2], Student[3], Student[4], Student[5], Student[6], Student[7]])
    def test_distinct6(self):
        result = select(s for s in Student).distinct()
        self.assertEquals(result, [Student[1], Student[2], Student[3], Student[4], Student[5], Student[6], Student[7]])
    def test_not_null1(self):
        q = select(g for g in Group if '123-45-67' not in g.students.tel and g.dept == Department[1])
        not_null = "IS_NOT_NULL COLUMN student-1 tel" in (" ".join(str(i) for i in flatten(q._translator.conditions)))
        self.assertEquals(not_null, True)
        self.assertEquals(q[:], [Group[101]])
    def test_not_null2(self):
        q = select(g for g in Group if 'John' not in g.students.name and g.dept == Department[1])
        not_null = "IS_NOT_NULL COLUMN student-1 name" in (" ".join(str(i) for i in flatten(q._translator.conditions)))
        self.assertEquals(not_null, False)
        self.assertEquals(q[:], [Group[101]])
    def test_chain_of_attrs_inside_for1(self):
        result = select(s for d in Department if d.number == 2 for s in d.groups.students)[:]
        self.assertEquals(result, [Student[4], Student[5], Student[6], Student[7]])
    def test_chain_of_attrs_inside_for2(self):
        pony.options.SIMPLE_ALIASES = False
        result = select(s for d in Department if d.number == 2 for s in d.groups.students)[:]
        self.assertEquals(result, [Student[4], Student[5], Student[6], Student[7]])
        pony.options.SIMPLE_ALIASES = True
    def test_non_entity_result1(self):
        result = select((s.name, s.group.number) for s in Student if s.name.startswith("J"))[:]
        self.assertEquals(result, [(u'Jing Xia', 102), (u'John Smith', 101)])
    def test_non_entity_result2(self):
        result = select((s.dob.year, s.group.number) for s in Student)[:]
        self.assertEquals(result, [(1988, 102), (1989, 101), (1990, 101), (1990, 102), (1991, 101), (1991, 102)])
    def test_non_entity_result3(self):
        result = select(s.dob.year for s in Student).without_distinct()
        self.assertEquals(result, [1991, 1990, 1989, 1990, 1991, 1990, 1988])
        result = select(s.dob.year for s in Student)[:]  # test the last query didn't override the cached one
        self.assertEquals(result, [1988, 1989, 1990, 1991])
    def test_non_entity_result3a(self):
        result = select(s.dob.year for s in Student)[:]
        self.assertEquals(result, [1988, 1989, 1990, 1991])
    def test_non_entity_result4(self):
        result = set(select(s.name for s in Student if s.name.startswith('M')))
        self.assertEquals(result, set([u'Matthew Reed', u'Maria Ionescu']))
    def test_non_entity_result5(self):
        result = select((s.group, s.dob) for s in Student if s.group == Group[101])[:]
        self.assertEquals(result, [(Group[101], date(1989, 2, 5)), (Group[101], date(1990, 11, 26)), (Group[101], date(1991, 3, 20))])
    def test_non_entity_result6(self):
        result = select((c, s) for s in Student for c in Course if c.semester == 1 and s.id < 3)[:]
        self.assertEquals(result, [(Course[u'Linear Algebra',1], Student[1]), (Course[u'Linear Algebra',1],
            Student[2]), (Course[u'Web Design',1], Student[1]), (Course[u'Web Design',1], Student[2])])
    def test_non_entity7(self):
        result = select(s for s in Student if (s.name, s.dob) not in (((s2.name, s2.dob) for s2 in Student if s.group.number == 101)))[:]
        self.assertEquals(result, [Student[4], Student[5], Student[6], Student[7]])
    @raises_exception(IncomparableTypesError, "Incomparable types 'int' and 'Set of Student' in expression: g.number == g.students")
    def test_incompartible_types(self):
        select(g for g in Group if g.number == g.students)
    @raises_exception(TranslationError, "External parameter 'x' cannot be used as query result")
    def test_external_param1(self):
        x = Student[1]
        select(x for s in Student)
    def test_external_param2(self):
        x = Student[1]
        result = select(s for s in Student if s.name != x.name)[:]
        self.assertEquals(result, [Student[2], Student[3], Student[4], Student[5], Student[6], Student[7]])
    @raises_exception(TypeError, "Use select(...) function or Group.select(...) method for iteration")
    def test_exception1(self):
        for g in Group: print g.number
    @raises_exception(MultipleObjectsFoundError, "Multiple objects were found. Use select(...) to retrieve them")
    def test_exception2(self):
         get(s for s in Student)
    def test_exists(self):
        result = exists(s for s in Student)
    @raises_exception(ExprEvalError, "db.FooBar raises AttributeError: 'TestDatabase' object has no attribute 'FooBar'")
    def test_entity_not_found(self):
        select(s for s in db.Student for g in db.FooBar)
    def test_keyargs1(self):
        result = select(s for s in Student if s.dob < date(year=1990, month=10, day=20))[:]
        self.assertEquals(result, [Student[3], Student[4], Student[6], Student[7]])
    def test_query_as_string1(self):
        result = select('s for s in Student if 3 <= s.gpa < 4')[:]
        self.assertEquals(result, [Student[1], Student[2], Student[4], Student[5], Student[6], Student[7]])
    def test_query_as_string2(self):
        result = select('s for s in db.Student if 3 <= s.gpa < 4')[:]
        self.assertEquals(result, [Student[1], Student[2], Student[4], Student[5], Student[6], Student[7]])
    def test_str_subclasses(self):
        result = select(d for d in Department for g in d.groups for c in d.courses if g.number == 106 and c.name.startswith('T'))[:]
        self.assertEquals(result, [Department[3]])
    def test_unicode_subclass(self):
        class Unicode2(unicode):
            pass
        u2 = Unicode2(u'\xf0')
        select(s for s in Student if len(u2) == 1)
        
if __name__ == "__main__":
    unittest.main()