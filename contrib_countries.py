""" Detect and analyze countries for Git / Github contributors
"""

from os.path import exists
import json
import re
import github3
from subprocess import check_call
from pprint import pprint

import numpy as np

import pandas as pd

from gputils import GH, lupdate, Repo, gh_user2ev_emails

# Country data from various sources.  See process_countries.py
country_data = pd.read_csv('country_data.csv')

# Variables as shortcuts
COUNTRY_NAMES = country_data['country_name']
COUNTRY_CODES = country_data['country_code']


# Locations for Github users where location string is not useful or absent.
# Data from web-stalking.
# Keys are Github users.
# Values are location strings, to be processed by location2country

GH_USER2LOCATION = {
    # https://www.ocf.berkeley.edu/~antonyl/research.html
    'anntzer': 'Bordeaux, France',
    # https://www.oreilly.com/people/ben-root
    # https://www.bloomberg.com/research/stocks/private/snapshot.asp?privcapId=4640588
    'WeatherGod': 'Lexington, MA, USA',
    # https://www.physics.utoronto.ca/%7Eesalesde/
    # https://twitter.com/QuLogic
    'QuLogic': 'Toronto, Canada',
    # Probably
    # https://www.researchgate.net/profile/Jae-Joon_Lee
    # See: https://github.com/astropy/pyregion/graphs/contributors
    'leejjoon': 'Daejeon, South Korea',
    # iki.fi email address
    'pv': 'Finland',
    # I know Eric.
    'eric-jones': 'Austin, TX',
    # https://vorpus.org/
    'njsmith': 'Berkeley, CA',
    # https://www.linkedin.com/in/allan-haldane-486510131/
    'ahaldane': 'Philadelphia, Pennsylvania, USA',
    # Works at Enthought. Enthought based in Austin, Texas. Most
    # recent commits UTC-8.
    'rkern': 'Austin, TX',
    # Was in Berlin in 2011.
    # https://wiki.kubuntu.org/JulianTaylor/MOTUApplication
    # Now seems to be in the European Southern Observatory near Munich
    # www.eso.org/~jagonzal/ADASS-2016/P6-11/P6-11.tex
    'juliantaylor': 'Bayern, Germany',
    # I know him via BIDS.
    'mattip': 'Israel',
    # Stefan vdW told me.
    'seberg': 'Göttingen, Germany',
    # Warren had an Enthought address until 2012 in the Scipy logs.  Also this:
    # https://www.instantcheckmate.com/people/warren-weckesser/
    'WarrenWeckesser': 'Austin, Texas',
    # Found: alex <argriffi@ncsu.edu>, author of
    # https://github.com/scipy/scipy/commit/3e8cb71f0118b1603f42b8aafb97aa0452401a1e
    'alexbrc': 'North Carolina, USA',
    # https://brae.calpoly.edu/faculty-and-staff-haberland
    'mdhaber': 'San Luis Obispo, CA, USA',
    # In git log: Lars Buitinck <larsmans@gmail.com>
    # https://www.linkedin.com/in/larsbuitinck/
    'larsmans': 'Amsterdam, Netherlands',
    # http://staff.washington.edu/larsoner/
    'larsoner': 'Seattle, USA',
    # http://www.ajoly.org/
    'arjoly': 'Liège, BEL',
    # https://team.inria.fr/parietal/loic-esteve-takes-a-permanent-position-at-inria-paris/
    'lesteve': 'Paris, FRA',
    # https://jmetzen.github.io/pages/about.html
    'jmetzen': 'Renningen, Germany',
    # https://demuc.de
    'ahojnnes': 'Zurich, Switzerland',
    # http://svi.cnrs.fr/spip/spip.php?article27
    'emmanuelle': 'Aubervilliers, FRA',
    # https://www.lfd.uci.edu/~gohlke/
    'cgohlke': 'Irvine, California, USA',
    # https://brage.bibsys.no/xmlui/handle/11250/247388
    'josteinbf': 'Oslo, Norway',
    # https://www.linkedin.com/in/chris-colbert-89699b7/
    'sccolbert': 'Austin, Texas',
    # http://warmspringwinds.github.io/about/
    'warmspringwinds': 'Baltimore, Maryland, USA',
    # http://www.chadfulton.com/
    'ChadFulton': 'USA',
    # Via Google: http://dept.stat.lsa.umich.edu/~kshedden/
    'kshedden': 'Michigan, USA',
    # https://www.linkedin.com/in/brock-mendel-76287a83/
    'jbrockmendel': 'San Francisco, USA',
    # In git log: Justin Grana <jg3705a@student.american.edu>
    'j-grana6': 'Washington DC, USA',
    # https://www.linkedin.com/in/pquackenbush/
    # Github location "Baghdad on the Bayou" could be Houston, which fits
    # above:
    # https://www.houstonpress.com/news/houston-101-yet-another-new-nickname-for-the-bayou-city-er-space-city-um-h-town-6738937
    'thequackdaddy': 'Houston, Texas',
    # https://www.bartonbaker.us
    'bartbkr': 'Rhode Island, USA',
    # This commit by yogabonito has email aleksandar.karakas@student.tugraz.at
    # https://github.com/statsmodels/statsmodels/commit/bf2d2b0d0cf76d99149503aee17925eaf4d117c4
    'yogabonito': 'Graz, Austria',
    # https://tomaugspurger.github.io/pages/about.html
    'TomAugspurger': 'Des Moines, USA',
    # https://www.linkedin.com/in/jeff-reback-3a20876/
    'jreback': 'NYC, USA',
    # I emailed them and they replied.
    'gfyoung': 'USA',
    # https://jorisvandenbossche.github.io/pages/about.html
    'jorisvandenbossche': 'Paris, France',
    # Has email terji78@gmail.com . Gives T Petersen from:
    # https://mail.python.org/pipermail/tutor/2005-May/038446.html
    # Discussing a chess program, suggesting
    # https://chess-db.com/public/pinfo.jsp?id=7200293
    # Above profile has 1978 birth year matching terji78.
    'topper-123': 'Faroe Islands',
    # https://directory.science.mq.edu.au/users/tjames
    'aragilar': 'Sydney, AUS',
    # https://www.linkedin.com/in/smichr/
    'smichr': 'Minneapolis, USA',
    # Thomas tells me via email he's based in the UK though working for
    # https://www.xfel.eu
    'takluyver': 'UK',
    # Lists the HDF group as employer
    'ajelenak-thg': 'Urbana-Champaign, USA',
    # Email listed as <aaron.parsons@diamond.ac.uk>
    # https://www.diamond.ac.uk/Home/ContactUs.html
    'aaron-parsons': 'Didcot, UK',
    # Probably
    # https://www.xfel.eu/facility/instruments/scs/scs_group_members/index_eng.html
    'tecki': 'Schenefeld, Germany',
    # Lists employer as Oak Ridge National Laboratory
    'sethrj': 'Tennessee, USA',
    # Git log has email John Kirkham <kirkhamj@janelia.hhmi.org>
    # https://www.janelia.org/
    'jakirkham': 'Virginia, USA',
    # http://consulting.behnel.de/
    'scoder': 'München, Germany',
    # https://www.linkedin.com/in/robert-bradshaw-1b48a07/
    'robertwb': 'Seattle, USA',
    # Github page lists noodle-app.io, which fits with
    # https://www.linkedin.com/in/mark-florisson-742a0175/
    'markflorisson': 'London, UK',
    # By looking at git shortlog on the Cython repository, this
    # appears to be Kurt Smith.  Last email address in log was
    # Enthought
    'invalid-email-address': 'USA',
    # Email in git log is "zaur <aintellimath@gmail.com>"
    # We also see "intellimath" Zaur Shibzukhov <szport@gmail.com>
    # Github user intellimath based in Moscow
    'aintellimath': 'Moscow, Russia',
    # Affiliation listed as Faculty of Physics, Moscow State University,
    # Moscow, Russia in https://peerj.com/preprints/2083
    # https://skirpichev.github.io blog has me@skirpichev.msk.ru as contact
    # address.
    'skirpichev': 'Moscow, Russia',
    # Maybe https://theorie.physik.uni-konstanz.de/jrioux/pdf/Rioux_cv.pdf
    # Thesis mentions sympy
    # https://tspace.library.utoronto.ca/bitstream/1807/31919/1/Rioux_Julien_201108_PhD_thesis.pdf
    'jrioux': 'Konstanz, Germany',
    # Email address in git log is Raoul Bourquin <raoulb@bluewin.ch>
    # Does not appear to this guy, who is Github user raoulbq (from Scipy
    # commit log):
    # https://www.research-collection.ethz.ch/handle/20.500.11850/183094
    'raoulb': 'Switzerland',
    # Github repo leads to Math 405 lectures, which leads to
    # http://www.math.ubc.ca/~cbm/
    'cbm755': 'Canada',
    # Git log has jegerjensen <jensen.oyvind@gmail.com> and
    # Øyvind Jensen <jensen.oyvind@gmail.com>
    # Github has fork of AMGXqGPU library. An 'Øyvind Jensen" is an author on 
    # https://www.researchgate.net/publication/318949247_GPU_implementation_of_Kampmann-Wagner_numerical_precipitation_models
    # and works in the Institute of Energy Technology, in Norway.
    'jegerjensen': 'Lillestrøm, Norway',
    # Google search first hit: https://users.isy.liu.se/en/es/oscarg/
    # Photo matches Github profile
    'oscargus': 'Linköping, Sweden',
    # Second pass, back to Numpy again
    # https://www.linkedin.com/in/jay-bourque-214b3341/
    'jayvius': 'Austin, Texas',
    # UTC-6
    # Xoviat appears to be Paul Dao:
    # http://vtk.1045678.n5.nabble.com/PYPI-wheels-td5745394.html
    # Maybe USA.
    'xoviat': 'N/K',
    # https://www.linkedin.com/in/han-genuit-0b125253
    # Working at:
    # https://www.differ.nl/about-us/people/search?name=Han+Genuit
    # Probably same as J.W.Genuit from:
    # https://sourceforge.net/p/pytables/mailman/message/26926819/
    '87': 'Eindhoven, Netherlands',
    # UTC-5
    # Going with:
    # https://www.linkedin.com/in/eric-moore-18292032
    # because he has forked the NRRD reading repository
    'ewmoore': 'Pennsylvania, USA',
    # Note same user name on LinkedIn
    # https://www.linkedin.com/in/adbugger/?originalSubdomain=in
    'adbugger': 'Telangana, India',
    # Says he works with Google on Github page, and
    # https://www.linkedin.com/in/paul-van-mulbregt-bb00412/
    'pvanmulbregt': 'Boston, USA',
    # https://www.linkedin.com/in/abraham-escalante-68538691/
    # Profile photo is the same.  Did his Scipy work from Mexico.
    'aeklant': 'Ontario, Canada',
    # http://panm19.math.cas.cz/prednasky/PANM19_Robert_Cimrman.pdf
    'rc': 'Czechia',
    # Matches Github email address
    # https://www.algopt.informatik.uni-kiel.de/en/team/m.sc.-joscha-reimer
    'jor-': 'Kiel, Germany',
    # https://www.uva.nl/en/profile/a/r/a.archibald/a.archibald.html?1556896598934
    'aarchiba': 'Amsterdam, Netherlands',
    # I worked with Chris
    'cburns': 'Berkeley, USA',
    # https://mail.python.org/pipermail/scipy-user/2009-March/020175.html has
    # email is from http://cs.uiuc.edu, matches:
    # https://www.linkedin.com/in/nathan-bell-65963915
    'wnbell': 'San Francisco, USA',
    # https://groups.google.com/d/msg/pydata/kPAg3l9vLQI/gAusKjYxQUIJ
    # Address is mattknox.ca@gmail.com. Mentions https://github.com/keeganmccallum
    # who give location as Canada.  UTC-8 in 2008.
    # Maybe https://www.linkedin.com/in/matt-knox-37537217
    '+matt_knox': 'CAN',
    # I know Tom
    # https://www.linkedin.com/in/thomas-waite-04354a4/
    '+tom_waite': 'Berkeley, USA',
    # From email address stevech1097@yahoo.com.au
    '+steve_chaplin': 'AUS',
    # Universitat Bremen as employer
    'andreas-h': 'Bremen, Germany',
    # http://www.tonysyu.com
    'tonysyu': 'Austin, Texas',
    # UTC+3. Python, C++. Maybe:
    # https://www.linkedin.com/in/kniazevnikita/?locale=en_US
    'Kojoley': 'Russia',
    # UTC+1. Maybe Peter Wurtz writing thesis on this page:
    # https://www.physik.uni-kl.de/en/ag-ott/publications/phd-and-diploma-thesis
    'pwuertz': 'Kaiserslautern, Germany',
    # Could be author on https://www.nature.com/articles/s41598-018-26267-x
    # at Institute for Theoretical Physics, TU Wien.  UTC+1 commits.
    'thisch': 'Vienna, AUT',
    # I know Paul.
    'ivanov': 'Berkeley, CA',
    # https://www.esrl.noaa.gov/psd/people/jeffrey.s.whitaker/
    'jswhit': 'Colorado, USA',
    # Probably https://digitalfellows.commons.gc.cuny.edu/?team=hannah-aizenman
    # because of cs102 repository mentioning CCNY, and
    # https://www.ccny.cuny.edu/compsci/faculty-office-hours
    'story645': 'NY, USA',
    # From git log: Michiel de Hoon
    # One entry in git log has: Michiel de Hoon
    # <mdehoon@tkx294.genome.gsc.riken.jp> - so:
    # https://acgt.riken.jp/?page_id=115
    'mdehoon': 'Yokohama, Japan',
    # https://www2.le.ac.uk/departments/physics/people/victorzabalza
    'zblz': 'Leicester, UK',
    # I can't find him now, but at the time of contribution, he
    # was an astronomer in Bonn
    # https://academic.oup.com/mnras/article/394/4/2223/1207223
    # https://astro.uni-bonn.de/~rschaaf/Python2008/
    'mmetz-bn': 'Bonn, Germany',
    # http://www.kemaleren.com/
    # https://www.linkedin.com/in/kemaleren/
    'kemaleren': 'Pennsylvania, USA',
    # https://www.linkedin.com/in/diemert/
    # via https://scikit-learn.org/stable/testimonials/testimonials.html
    'oddskool': 'Grenoble, FRA',
    # Google search for Bertrand Thirion
    'bthirion': 'Saclay, FRA',
    # Right there on the Github page
    'NicolasHug': 'New York, USA',
    # https://www.linkedin.com/in/maheshakya/
    'maheshakya': 'Utah, USA',
    # ('UTC-05:00', 22), ('UTC-06:00', 9))
    # Two hits for Chris Bartak on LinkedIn, neither with programming
    # experience, both in the US.  Second is social psychology student, but no
    # sign of programming in 2015 thesis:
    # https://shareok.org/handle/11244/15488
    # Facebook profiles don't look interesting. Maybe:
    # https://wearerivet.com/about-us/
    # but searches and timezones suggest USA.
    'chris-b1': 'N/K',
    # https://pietrobattiston.it/Curriculum_Vitae_en.pdf
    'toobaz': 'Trento, Italy',
    # https://en.wikipedia.org/wiki/Lord_Vetinari
    # UTC+1
    'h-vetinari': 'N/K',
    # Mario Pernici <mario.pernici@gmail.com> in git log.
    # https://arxiv.org/pdf/1805.04037.pdf mentions Python / SageMath
    'pernici': 'Milano, ITA',
    # https://www.ibisc.univ-evry.fr/~sivanov
    'scolobb': 'Saclay, FRA',
    # http://parsoyaarihant.github.io/
    'parsoyaarihant': 'Mumbai, IND',
    # By number of cmmmits this should be Github user normalhuman
    # with name (in git log) Leonid Kovalev
    # https://normalhuman.github.io/progress/report refers to
    # mathematics courses at http://coursecatalog.syr.edu
    # https://github.com/drlvk/drlvk.github.io/blob/master/bookmarklets.html
    # also refers to syr.edu.
    # Sure enough:
    # http://thecollege.syr.edu/people/faculty/pages/math/kovalev-leonid.html
    # Dr Leonid V. Kovalev (drvlk)
    'normalhuman': 'New York, USA',
    'drlvk': 'New York, USA',
    # https://sidhantnagpal.com/
    'sidhantnagpal': 'Dehli, IND',
    # https://valglad.github.io/ : was at Oxford in 2017
    # https://github.com/sympy/sympy/wiki/GSoC-2017-Application-Valeriia-Gladkova:-Group-Theory
    # https://arxiv.org/abs/1810.08792
    # Email for paper above still Oxford
    'valglad': 'Oxford, GBR',
    # UTC+1.  Git log has oscar.j.benjamin@gmail.com . Probably
    # http://www.bristol.ac.uk/engineering/people/oscar-j-benjamin/index.html
    'oscarbenjamin': 'Bristol, UK',
    # https://jashan498.github.io/blog/
    'jashan498': 'Patiala, IND',
    # https://blog.krastanov.org/staticprerenders/resume.html
    'Krastanov': 'Yale, USA',
    # Via Google: http://www.math.toronto.edu/siefkenj/homepage/index.html
    # Link back to Github page
    # http://www.math.toronto.edu/siefkenj/homepage/index.html#software
    'siefkenj': 'Toronto, CAN',
    # Brian Granger (co-lead on Jupyter)
    # Was teaching Physics at CalPoly, now works for AWS
    # https://www.linkedin.com/in/brian-granger-b9998662
    'ellisonbg': 'Los Osos, USA',
    # http://rpmuller.github.io/
    # https://cs.sandia.gov/~rmuller/
    'rpmuller': 'Albuquerque, USA',
    # https://yathartha22.github.io/about
    'Yathartha22': 'Dwarahat, IND',
    # Vinzent Steinberg
    # Affiliation from https://arxiv.org/abs/1809.03828
    # Frankfurt Institute for Advanced Studies
    # arXiv.org email is gmail address in Git log
    'vks': 'Frankfurt, Germany',
    # This LinkedIn profile as the same photo as GH profile
    # https://www.linkedin.com/in/gilbertgede
    # GH pages link to papers from UC Davis, that match.
    'gilbertgede': 'Bay Area, USA',
    # Vladimir Perić, vlada.peric@gmail.com
    # https://github.com/asmeurer/sympy/wiki/GSoC-2011-report:-Vladimir-Peric%CC%81:-Porting-to-Python-3
    # "Faculty of Electrical Engineering, Czech Technical University in
    # Prague". Matches https://www.linkedin.com/in/vladimir-p-41546a130/
    # Blog linked on GH page reports mock lirary for Matlab, also on page
    # above.
    # Timezones: (('UTC+01:00', 30), ('UTC+02:00', 90), ('UTC-08:00', 11),
    # ('UTC-07:00', 2))
    'vperic': 'Prague, Czechia',
    # https://www.linkedin.com/in/hargup from GH pages.
    'hargup': 'Pune, IND',
    # Facebook page linked from GH pages:
    # https://www.facebook.com/akash.vaish.9
    # "Lives in Goa"
    'akash9712': 'Goa, IND',
    # Emails from mail.arizone.edu in 2019, and sunbelt-medical.com in 2018
    # (based in Tucson AZ)
    # Timezones: (('UTC-07:00', 64),)
    'ethankward': 'Tucson, USA',
    # https://www.linkedin.com/in/addison-cugini-a590a868/
    # GSoC, Calpoly, then Apple.
    'addisonc': 'Sunnyvale, USA',
    # https://github.com/sympy/sympy/wiki/GSoC-2018-Application-Adwait-Baokar:-Implementation-of-Vector-Integration
    # Leads to:
    # https://www.linkedin.com/in/adwait-baokar-429587114/
    'abaokar-07': 'Indore, India',
    # (('UTC-04:00', 82), ('UTC-05:00', 6))
    # Commits from 2013-2015
    # https://marc.info/?l=python-bugs-list&m=134188728723063&w=2
    'hacman': 'N/K',
    # https://github.com/sympy/sympy/wiki/GSoC-2017-Report-Arif-Ahmed-:-Integration-over-Polytopes
    # https://www.linkedin.com/in/arif-ahmed-101856a5
    # Timezones: (('UTC+05:30', 86),)
    'ArifAhmed1995': 'Goa, IND',
    # avishrivastava11.github.io
    'avishrivastava11': 'Goa, IND',
    # GH page "Junior Undergraduate ,Mathematics and Computing at Indian
    # Institute of Technology(BHU),Varanasi India"
    'jmig5776': "Varanasi, India",
    # GH page "Sophomore, Mathematics and Computing at IIT (BHU) Varanasi"
    'RituRajSingh878': 'Varanasi, India',
    # Same photo, username as GH page: https://www.linkedin.com/in/lazovich
    # Cambridge, Massachusetts
    # Timezones: (('UTC-04:00', 5), ('UTC-05:00', 64))
    'lazovich': 'Cambridge, USA',
    # GH pages "I'm pursuing my btech UG from IIIT Allahabad."
    'RavicharanN': 'Allahabad, IND',
    # GH page: "UnderGrad Student at IIT Guwahati."
    'Subhash-Saurabh': 'Guwahati, IND',
    # Email at iiitmanipur.ac.in
    # https://groups.google.com/d/msg/hsf-forum/rHHsZQ5aslc/4Zlld9s1GQAJ
    'divyanshu132': 'Manipur, IND',
    # GH page links to https://sites.google.com/site/chaiwahwucv
    'postvakje': 'Yorktown Heights, USA',
    # Commits from 2012-2015
    # https://survivejs.com/blog/codemod-interview has same logo as GH page,
    # and points back to GH pages blog.  "I am front-end developer from India".
    # Timezones: (('UTC+05:30', 46), ('UTC-08:00', 7), ('UTC-07:00', 3))
    'vramana': 'IND',
    # Nick Curtis, conn.edu address. Company AMD research.
    # Seems to be some AMD facility at Boston, from
    # https://www.linkedin.com/in/curtis-wickman-06b2a515/#experience-section
    # Timezones: (('UTC-04:00', 54),)
    'arghdos': 'USA',
    # https://www.linkedin.com/in/briangregoryjorgensen
    # Same photo as github
    'b33j0r': 'Phoenix, USA',
    # Email address; nothing else go on.
    'stevech1097@yahoo.com.au': 'AUS',
    # See find_gh_users.
    # https://www.linkedin.com/in/dmitrey-kroshko-a729aa22/
    '+dmitrey_kroshko': 'Ukraine',
    # See find_gh_users.  Workst at NIST Center for Neutron Research.
    "pkienzle": "Gaithersburg, USA",
    # Matplotlib git log records email as "pado@passoire.fr"
    '+alexis_bienvenue': 'FRA',
    # See find_gh_users.
    # From https://team.inria.fr/parietal/schwarty/
    '+yannick_schwartz': 'Saclay, France',
    # I know Brian
    '+brian_hawthorne': 'USA',
    # LinkedIn page with same photo as Github page
    # https://www.linkedin.com/in/matthieu-perrot-225ab01b/
    'MatthieuPerrot': 'Paris, France',
    # See find_gh_user
    # https://web.archive.org/web/20110826071405/http://robert-code.blogspot.com/2007/05/grbner-basis-hey-my-first-blog-entry-so.html
    "+robert_schwarz": "Heidelberg, Germany",
    # https://www.linkedin.com/in/domspad links to Github page
    'domspad': 'Austin, TX',
    # I know Yarik
    'yarikoptic': 'USA',
    # See find_gh_users
    # https://www.linkedin.com/in/tim-at-bitsofbits
    'bitsofbits': 'Scottsdale, USA',
    # https://www.aero.iitb.ac.in/~prabhu
    'prabhuramachandran': 'Bombay, IND',
    # This is a bot
    'meeseeksmachine': 'N/K',
    # An email in git log is ncsu.edu.  Alex Griffing NCSU author on
    # https://doi.org/10.1093/molbev/msw114
    'argriffing': 'North Carolina, USA',
    # GH pages links to:
    # https://www.linkedin.com/in/michael-seifert-1045b7124
    'MSeifert04': 'Heidelberg, Germany',
    # https://www.research-collection.ethz.ch/handle/20.500.11850/183094
    # matches email address: raoul.bourquin@sam.math.ethz.ch
    # Also https://genealogy.math.ndsu.nodak.edu/id.php?id=220903
    'raoulbq': 'Switzerland',
    # TZ UTC are all older than 2010, and seem to be SVN commits.  More recent
    # are UTC-7, UTC-8.  Nothing much else to go on.
    'jrevans': 'N/K',
    # Program making extensive use of matplotlib author Danial G Hyams:
    # https://karczmarczuk.users.greyc.fr/TEACH/ProgSci/Progs/hyamsMoody.py
    # https://www.linkedin.com/in/daniel-g-hyams-14453663 leads to
    # http://www.curveexpert.net
    # Downloading the trial version of CurveExport Pro, finds bundled copies of
    # Numpy, Scipy, Matplotlib, wxPython.  GH repositories for this user include
    # wxPython, pyinstaller.  TZ UTC-4,-5
    'dhyams': 'Huntsville, USA',
    # Likely https://www.tcm.phy.cam.ac.uk/~nn245/index.html#aboutme
    # "Besides physics, I've been interested in Open Source software since
    # 1995, when I first installed Linux on my computer. Over the years, I have
    # gathered all kinds of experience in programming, system and network
    # adminstration. ". Also mentions D languagen, and has fork of D language
    # compiler on Github page.  Matches:
    # https://www.linkedin.com/in/norbert-nemec
    # (Education Regensburg, Cambridge physics 2008-9)
    'NNemec': 'Munich, Germany',
    # Working at Space Telescope Science Institute
    'jaytmiller': 'Baltimore, USA',
    # Log email megies@geophysik.uni-muenchen.de matches
    # https://www.geophysik.uni-muenchen.de/Members/megies/publications
    'megies': 'Munich, Germany',
    # Account has fork of python-neo, to which he is the main contributor:
    # https://github.com/toddrjen/python-neo/graphs/contributors
    # This leads to:
    # https://www.frontiersin.org/articles/10.3389/fninf.2014.00010/full
    # which leads to:
    # https://www.linkedin.com/in/todd-jennings-23309811
    'toddrjen': 'Boston, USA',
    # GH page leads to
    # http://gael-varoquaux.info/about.html
    'GaelVaroquaux': 'Saclay, FRA',
    # GH page links to Saclay and Logilab.fr, leading to
    # https://www.linkedin.com/in/vincent-michel-79526427/
    'vmichel': 'Paris, FRA',
    # GH page links to https://github.com/UIUC-data-mining
    # leading to http://dm1.cs.uiuc.edu/alumni.html leading to
    # https://www.linkedin.com/in/hlin117/
    'hlin117': 'Champaign, USA',
    # https://scikit-learn.org/stable/whats_new.html lists name
    # as Jeremie du Boisberranger.  Listed as INRIA in
    # https://github.com/glemaitre/pyparis-2018-sklearn/blob/master/README.md
    # Listed in research engineers at https://team.inria.fr/parietal/team-members
    'jeremiedbb': 'Saclay, FRA',
    # Name Vincent Dubourg leads to:
    # Scikit-learn paper https://arxiv.org/abs/1201.0490 affiliation of
    # Institute for Advanced Mechanics (IFMA), leads to
    # https://sites.google.com/site/vincentdubourg/software
    'dubourg': "Cournon d'Auvergne, FRA",
    # Email address rob@zinkov.com leads to https://www.zinkov.com/about
    # Was at Indiana University.
    'zaxtax': 'Oxford, UK',
    # GH pages
    'eickenberg': 'Berkeley, USA',
    # GH pages
    'albertcthomas': 'Paris, FRA',
    # From feed contents, likely to be
    # https://twitter.com/michaelhgraber
    # Repositories on neural signalling.
    # Leading to https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0081177
    # This suggests Switzerland, but all commits UTC+9.  Give up.
    'michigraber': 'N/K',
    # GH pages point to wedding in Stanford, South Africa  TZ UTC+2, which is
    # compatible.
    'holtzhau': 'ZAF',
    # https://www.linkedin.com/in/rishabhraj mentions GSoC scikit-image
    'sharky93': 'Hyderabad Area, India',
    # GH page points to http://zplab.wustl.edu/
    'zpincus': 'St. Louis, USA',
    # GH page points to https://www.linkedin.com/in/yl1986/
    'yl565': 'Charlestown, USA',
    # https://www.statsmodels.org/devel/release/version0.9.html points to
    # https://github.com/statsmodels/statsmodels/pull/4176 and attributes it
    # to Terence L van Zyl
    # https://www.wits.ac.za/staff/academic-a-z-listing/v/terencevanzylwitsacza/
    # https://www.linkedin.com/in/terence-van-zyl-b9b00b4
    'tvanzyl': 'Johannesburg, ZAF',
    # 943 commits to Pandas, Github account deleted.
    # Github username was y-p.  Email yoval@gmx.com
    # TZ ('UTC+03:00', 230), ('UTC+02:00', 555), ('UTC-08:00', 97),
    # ('UTC-07:00', 61).  Main time zones compatible with Isreal.
    # https://groups.google.com/forum/#!topic/hasadna11/yDqHhK5FiOo has Yoval P
    # writing in Hebrew.
    '+y_p': 'ISR',
    # Maybe:
    # https://www.linkedin.com/in/kieran-o-mahony-661759132
    # C++ and Python listed as skills.  Main project on GH page
    # is https://github.com/Komnomnomnom/swigibpy, Python API for C++ API.
    # Timezones (('UTC+01:00', 15), ('UTC+10:00', 19), ('UTC', 2),
    # ('UTC+11:00', 5), ('UTC-04:00', 2)); could be UK or Ireland with visits
    # to Australia.
    'Komnomnomnom': 'IRL',
    # Name Dieter Vandenbussche, email dvandenbussche@axioma.com leads to
    # https://www.linkedin.com/in/dieter-vandenbussche-b1b9a84/
    'dieterv77': 'Atlanta, USA',
    # GH page bio is "Dublin, Ireland"
    'reidy-p': 'Dublin, IRL',
    # Name Evan Wright, email name "evanpw"
    # Probably https://www.linkedin.com/in/evan-wright-01799341/
    # Lists Python and C++ skills, matching GH page, including C++
    # compiler.  Links to now-dead page math.sunysb.edu/~evanpw
    'evanpw': 'New York, USA',
    # Lists employer as Two Sigma Investments
    # https://en.wikipedia.org/wiki/Two_Sigma
    'bwignall': 'New York, USA',
    # GH bio is "Python/Java Developer, 23, UK"
    'alimcmaster1': 'UK',
    # http://gsoc2016.scrapinghub.com/mentors links GH user immerrr to
    # name Denis Shpektorov, leading to:
    # https://www.linkedin.com/in/dshpektorov/
    # This fits with Scrapinghub employment and Lua experience.
    'immerrr': 'Spain',
    # GH pages contact lists Florida, USA
    # Probably https://www.linkedin.com/in/gaborliptak
    'gliptak': 'Florida, USA',
    # Grant Roch
    # Google search reference to a John's Hopkins tennis
    # player, and name-address websites listing a Grant F Roch in Baltimore.
    # Zoominfo gets a Johns Hopkins table tennis person, and claims that a
    # Grant Roch works at Hartree Partners LP.
    # Whitepages lists the Baltimore Roch, and another in Wisconsin, with some
    # of the same names of relatives.
    # Google scholar search author:"Grant Roch" gives one paper
    # "Roch, Grant Francis. "Numerical Solutions of Electricity Market
    # Equilibrium and Collusion Models with AMPL and MATLAB." PhD diss., Johns
    # Hopkins University, 2004."
    # Maybe relevant:
    # http://gradsusr.org/pipermail/gradsusr/2008-March/006596.html
    # Timezones: (('UTC-04:00', 10), ('UTC-05:00', 10), ('UTC-08:00', 5))
    'rockg': 'USA',
    # Log email ends acdlabs.ru.  Leads to "ACD Moscow intranet"
    # Workplace listed as ACD/Labs
    'aparamon': 'RUS',
    # Emails at Enthought and wisc.edu.  Author of Cython book.
    # https://www.linkedin.com/in/kwmsmith/
    'kwmsmith': 'Austin, USA',
    # Tom Bachmann is German, but he was a student at Cambridge UK when he did
    # most of his Sympy work.  Now he's at MIT: http://tom-bachmann.com/
    'ness01': 'MIT, USA',
    # Linked from GH page: https://www.lidavidm.me/blog/about
    'lidavidm': 'New York, USA',
    # Git logs: Timothy Reluga, treluga@math.psu.edu
    # http://bio.psu.edu/directory/tcr2
    'zanzibar7': 'Pennsylvania, USA',
    # Sympy contributions in quantum computing
    # Search for Raymond Wong quantum computing reaches
    # https://www.cs.ucsb.edu/news/events/phd-proposal-raymond-wong-techniques-improving-resource-usage-quantum-circuits
    # and then: https://www.linkedin.com/in/raymond-wong-68aa5a28/
    # listing Python as a skill.
    # Timezones: (('UTC-08:00', 82), ('UTC-07:00', 45))
    'rwong': 'Bay Area, USA',
    # Mary Clark
    # https://github.com/sympy/sympy/wiki/GSOC-Report-2013-Mary-Clark:-Lie-Algebras
    # Leading to: https://www.linkedin.com/in/mary-clark-76406783/
    # with same picture as GH Page.  Working for Wolfram.
    'meclark256': 'Carmel, USA',
    # Maybe https://www.linkedin.com/in/pabpue
    # Name is Pablo Puente, Gmail name is pabpuedom suggesting
    # Pablo Puente Dominguez.  Search for "Pablo Puente Dominguez" leads to
    # programming competitor:
    # https://uva.onlinejudge.org/index.php?option=com_onlinejudge&Itemid=8&page=show_authorstats&userid=2001008
    # LinkedIn site mentions various programming contests.
    # Timezones: (('UTC+02:00', 45), ('UTC+01:00', 15))
    'ppuedom': 'Munich, Germany',
    # Top hit for Katja Sophie Hotz is
    # https://github.com/sympy/sympy/wiki/GSoC-2013-Application-Katja-Sophie-Hotz:-Faster-Algorithms-for-Polynomials-over-Algebraic-Number-Fields
    # I can't find anything relevant that is more recent, even with:
    # "Katja Sophie" (maths OR mathematics OR math)
    'katjasophie': 'Wien, AUT',
    # GH pages has.
    # "Thomas Baruchel, who is a french teacher in Philosophy and in Computer
    # science". Search for "Thomas Barachel" leads to:
    # https://twitter.com/baruchel also French teacher of philosophy, location
    # "Brest, France".
    'baruchel': 'Brest, FRA',
    # GH pages leads to http://anurags92.github.io/about
    'anurags92': 'Bengaluru, India',
    # Siddhanathan Shanmugam
    # GH user was siddhanathan, now deleted.  Last contribution was in 2012.
    # Nothing useful at archive.org
    # There's a student of the same name at Drexel:
    # https://dl.acm.org/citation.cfm?id=3122950
    # Another page suggests that this is GH user siddhanathan
    # https://icfp17.sigplan.org/profile/siddhanathanshanmugam
    # Timezones (('UTC+05:30', 40),)
    '+siddhanathan_shanmugam': 'Philadelphia, USA',
    # stanford.edu email, org given as "Stanford Physics/CS 2019"
    'jcreus': 'Stanford, USA',
    # Last commit 2016.
    # https://github.com/mon95/sympy/wiki/GSoC-2016-Application-James-Brandon-Milam:-Base-Class-and-Increased-Efficiency-for-Equation-of-Motion-Generators
    # At the time "University of Florida, Gainesville, Masters in Mechanical
    # Engineering" - therefore:
    # https://www.linkedin.com/in/jamesbmilam
    'jbm950': 'Gainesville, USA',
    # Bio says "SRE@Google", therefore:
    # https://www.linkedin.com/in/sahilshekhawat
    # Site reliability engineer, GSoC for PyDy, location "Ireland".
    # Timezones (('UTC+05:30', 36),)
    'sahilshekhawat': 'IRL',
    # GH pages about: "software engineer working in Vienna, Austria"
    'qcoh': 'Wien, AUT',
    # Last commit Sympy in 2013, email at calpoly.edu, presumably related to
    # https://digitalcommons.calpoly.edu/physsp/73/
    # Leads to: https://www.linkedin.com/in/matthewchoff
    # Credit risk analytics consultant at Wells Fargo
    'ottersmh': 'Bay Area, USA',
    # Last Sympy commit in 2013
    # https://github.com/gxyd/sympy/wiki/GSoC-2014-Application-Shipra-Banga-Building-the-New-Assumptions-Module
    # then at IIT Hyderabad, later working at Google.
    # https://ghcischedule.anitab.org/blog/speaker/shipra-banga/
    # Most recent Github commit in https://github.com/shiprabanga/writing-synthesis
    # Author: Shipra Banga <shiprab@shiprab-macbookpro2.roam.corp.google.com>
    # Date:   Fri Feb 15 02:51:58 2019 -0800
    # Assume she's in California now.
    'shiprabanga': 'USA',
    # https://eight1911.github.io links back to GH user page.
    'Eight1911': 'Providence, USA',
    # https://www.linkedin.com/in/shikhar-makhija-5b436087
    # is first of two hits on LinkedIn, and lists sketching, Python, algorithms
    # as top three skills. Location North West Delhi, Delhi, India.
    # Timezones: (('UTC+05:30', 33),)
    'Shikhar1998': 'Delhi, India',
    # GH pages about "I am a fifth year Integrated MTech student at
    # International Institute of Information Technology, Bangalore"
    # Affiliation on this paper implies she's still there:
    # https://arxiv.org/pdf/1811.12640v2.pdf
    'megh1241': 'Bangalore, IND',
    # GH pages links to CV, links to https://www.linkedin.com/in/sagar-bharadwaj-k-s/
    'SagarB-97': 'Bengaluru, IND',
    # UTC-4.  Google search for Dustin Gadal gives:
    # https://www.ic.gc.ca/app/scr/cc/CorporationsCanada/fdrlCrpDtls.html?corpId=9727019
    # giving Elseware Inc, based in Ontario.
    'Gadal': 'Ontario, CAN',
    # GH page gives work as Argonne National Laboratory
    'markdewing': 'Lemont, USA',
    # Address of first email to sympy mailing list starts 'pkrat'
    # https://groups.google.com/forum/#!searchin/sympy/Rathmann%7Csort:date/sympy/0WMK57uJd7s/QgGic7WZn3AJ
    # One email in git log is peter@ubuntu.ubuntu-domain
    # Peter Karl Rathmann did a Math PhD at Stanford, dated 1990
    # https://www.genealogy.math.ndsu.nodak.edu/id.php?id=87269
    # TZ UTC-8, UTC-7, compatible with California.  Maybe:
    'rathmann': 'USA',
    # Timezone UTC-3.  Google search gives a couple of plausible hits:
    # https://www.ic.unicamp.br/ensino/pg/quali/eqm-gabriell-orisaka
    # https://www.linkedin.com/in/gabriel-takeshi-orikasa-2a762991/
    # Maybe Brazil
    'gorisaka': 'BRA',
    # Company given as IIT Delhi
    'jtnydv25': 'Delhi, IND',
    # Name in git log is David Ju.  TZ UTC-8.  Nothing else I could find.
    'SgtMook': 'N/K',
    # https://github.com/sympy/sympy/wiki/GSoC-2019-Application-SHIKSHA-RAWAT-:-Benchmarks-and-performance
    # Location Birla Institute Of Technology,Mesra,Ranchi,India
    'shiksha11': 'Ranchi, IND',
    # Name in Sympy git log is Stephen Loo
    # Timezone UTC+8
    # https://twitter.com/stephenloo1 has Maths, Python listed in profile,
    # and retweets the Sympy 1.4 release tweet.
    # Twitter account location given as 香港 (Hong Kong), matching timezone.
    'shikil': 'Hong Kong, HKG',
    # http://shivanikohli.me/
    # Marquette University
    'shivanikohlii': 'Milwaukee, USA',
    # https://groups.google.com/d/msg/sympy/y67m39bqaY0/hdm8mCDRLD4J
    # "I'm second year postgraduate student in Saint-Petersburg Nuclear Physics
    # Institute".
    # https://www.linkedin.com/in/yuriy-demidov-40708646/
    'yuriy-demidov': 'Saint Petersburg, RUS',
    # Main contributor to this repo:
    # https://github.com/MPIBGC-TEE/CompartmentalSystems/graphs/contributors
    # https://github.com/MPIBGC-TEE page lists mamueller@bgc-jena.mpg.de
    'mamueller': 'Jena, Germany',
}


EXTRA_COUNTRIES = {
    'UK': 'GBR',
    'United Kingdom': 'GBR',
    'Italia': 'ITA',
    'Russia': 'RUS',
    'United States': 'USA',
}


# Regular expressions to apply to location string, resulting in 3-letter ISO
# country code.
def tw(word):
    # Match word, delineated fore and aft.
    return rf'(\W|^){word}(\W|$)'

COUNTRY_REGEXPS = (
    (tw('Seattle'), 'USA'),
    (tw('Berkeley'), 'USA'),
    (tw('Austin'), 'USA'),
    (tw('Chicago'), 'USA'),
    (tw('New York'), 'USA'),
    (tw('NYC'), 'USA'),
    (tw('Texas'), 'USA'),
    (tw('Arizona'), 'USA'),
    (tw('Denver'), 'USA'),
    (tw('Cincinnati'), 'USA'),
    (tw('Cleveland'), 'USA'),
    (tw('Philadelphia'), 'USA'),
    (tw('Ithaca'), 'USA'),
    (tw('Hawaii'), 'USA'),
    (tw('Boston'), 'USA'),
    (tw('Nashville'), 'USA'),
    (tw('California'), 'USA'),
    (tw('Bay Area'), 'USA'),
    (tw('East Bay, CA'), 'USA'),
    (tw('Raleigh'), 'USA'),
    (tw('Hancock'), 'USA'),
    (tw('Boulder'), 'USA'),
    (tw('Dunwoody'), 'USA'),
    (tw('San Francisco'), 'USA'),
    (tw('San Jose'), 'USA'),
    (tw('Oakland'), 'USA'),
    (tw('Merced'), 'USA'),
    (tw('Irvine'), 'USA'),
    (tw('San Diego'), 'USA'),
    (tw('Los Alamos'), 'USA'),
    (tw('Michigan'), 'USA'),
    (tw('Los Angeles'), 'USA'),
    (tw('Pittsburgh'), 'USA'),
    ('ABQ$', 'USA'),
    (tw('Pasadena'), 'USA'),
    (tw('Urbana'), 'USA'),
    (tw('Mountain View'), 'USA'),
    (tw('Albuquerque'), 'USA'),
    (tw('Stanford'), 'USA'),
    (tw('Atlanta'), 'USA'),
    (tw('Cambridge, MA'), 'USA'),
    (tw('Madison'), 'USA'),
    (tw('Darnestown'), 'USA'),
    (tw('Silver Spring'), 'USA'),
    (tw('Colbert'), 'USA'),
    (tw('Montreal'), 'CAN'),
    (tw('London'), 'GBR'),
    (tw('Bristol'), 'GBR'),
    (tw('Copenhagen'), 'DNK'),
    (tw('Helsinki'), 'FIN'),
    (r'Korea$', 'KOR'),
    (tw('Seoul'), 'KOR'),
    (tw('Paris'), 'FRA'),
    (tw('Saint Petersburg'), 'RUS'),
    (tw('Perm'), 'RUS'),
    (tw('Moscow'), 'RUS'),
    (tw('Mumbai'), 'IND'),
    (tw('Bombay'), 'IND'),
    (tw('Delhi'), 'IND'),
    (tw('Bengaluru'), 'IND'),
    (tw('Kharagpur'), 'IND'),
    (tw('Andhra Pradesh'), 'IND'),
    (tw('Kanpur'), 'IND'),
    (tw('Hyderabad'), 'IND'),
    (tw('Agartala'), 'IND'),
    (tw('Sydney'), 'AUS'),
    (tw('Minsk'), 'BLR'),
    (tw('Bologna'), 'ITA'),
    ('Brazil$', 'BRA'),
    (tw('Zurich'), 'CHE'),
    (tw('Bordeaux'), 'FRA'),
    ('Bremen$', 'DEU'),
    ('Saclay$', 'FRA'),
    ('Berlin$', 'DEU'),
    (tw('Poznan'), 'POL'),
    (tw('Tokyo'), 'JPN'),
    (tw('Oslo'), 'NOR'),
    (tw('Amersfoort'), 'NLD'),
    (r'IBM\s+.*[Ww]atson\s+[Rr]esearch\s+[Ll]ab', 'USA'),
    (tw('Champaign'), 'USA'),
    ('Washington[, ]*DC', 'USA'),
    ('Minnepolis, MN', 'USA'),
    (tw('Grenoble'), 'FRA'),
    (tw('Linz'), 'AUT'),
    (tw('Innsbruck'), 'AUT'),
    (tw('Ekaterinburg'), 'RUS'),
    (tw('Toronto'), 'CAN'),
    (tw('[Ii]stanbul'), 'TUR'),
    (tw('Goa'), 'IND'),
    (tw('Tel Aviv'), 'ISR'),
    (tw('Göteborg'), 'SWE'),
)


def location2countrish(location):
    """ Get last word as first guess at country from location string
    """
    if ';' in location:
        last = location.split(';')[-1]
    else:
        last = [p for p in location.split(',')][-1]
    last = last.strip()
    if last.endswith('.'):
        last = last[:-1]
    return last


def location2country(location):
    """ Estimate country from location string
    """
    if location is None:
        return None
    for reg, country in COUNTRY_REGEXPS:
        if re.search(reg, location):
            return country
    country = location2countrish(location)
    if country == 'N/K':
        return country
    found = find_country(country)
    if found:
        return found


def find_country(candidate):
    """ Estimate country from `candidate` string
    """
    is_iso = COUNTRY_CODES == candidate
    if np.any(is_iso):
        return COUNTRY_CODES.loc[is_iso].item()
    is_country = COUNTRY_NAMES == candidate
    if np.any(is_country):
        return COUNTRY_CODES.loc[is_country].item()
    if candidate in EXTRA_COUNTRIES:
        return EXTRA_COUNTRIES[candidate]


def gh_user2location(gh_user):
    """ Return location string for Github user specified in `gh_user`

    First check GH_USER2LOCATION dictionary, where we specify a location string
    by hand, for given Github user strings; otherwise return the location
    string from the user's Github profile.
    """
    if gh_user in GH_USER2LOCATION:
        return GH_USER2LOCATION[gh_user]
    user_data = USER_GETTER(gh_user)
    if user_data:
        return user_data['location']


def gh_user2country(gh_user):
    """ Return estimate of country for `gh_user`

    Get location string, and process to estimate country for location string.
    """
    location = gh_user2location(gh_user)
    if location is None:
        print(f'{gh_user} has no location')
        return
    country = location2country(location)
    if country is None:
        print(f'{gh_user} has location {location} but no country')
        return
    return country


class RepoGetter:
    """ Cache and return read data for repositories
    """

    def __init__(self):
        self._rcache = {}
        self._ccache = {}

    def get_repo(self, repo_name):
        if repo_name not in self._rcache:
            self._rcache[repo_name] = Repo(repo_name)
        return self._rcache[repo_name]

    def get_contributors(self, repo_name):
        repo = self.get_repo(repo_name)
        if repo_name not in self._ccache:
            self._ccache[repo_name] = repo.contributors()
        return self._ccache[repo_name]


REPO_GETTER = RepoGetter()


class UserGetter:
    """ Cache and return Github user data
    """

    def __init__(self, cache_fname=None):
        self._GH = GH
        self.cache_fname = cache_fname
        if cache_fname:
            self.load_cache()
        else:
            self.clear_cache()

    def load_cache(self):
        if self.cache_fname is None:
            raise ValueError('No cache_fname to load from')
        if not exists(self.cache_fname):
            self._cache = {}
            return
        with open(self.cache_fname, 'rt') as fobj:
            self._cache = json.load(fobj)

    def save_cache(self):
        if self.cache_fname is None:
            raise ValueError('No cache_fname to save to')
        with open(self.cache_fname, 'wt') as fobj:
            json.dump(self._cache, fobj)

    def clear_cache(self):
        self._cache = {}

    def __call__(self, gh_user):
        if gh_user not in self._cache:
            self._cache[gh_user] = self._get_gh_user(gh_user)
        return self._cache[gh_user]

    def _get_gh_user(self, gh_user):
        if gh_user.startswith('+') or gh_user in ('None',):
            return None
        return self._GH.user(gh_user).as_dict()


USER_GETTER = UserGetter('.user_cache.json')


# Make reporting user data prettier with custom dictionary.

def get_fields(obj):
    """ Get 'fields' attribute if present, otherwise return empty tuple

    Allows FieldDict below to process non-FieldDict dictionaries.
    """
    return getattr(obj, 'fields', ())


class FieldDict(dict):
    """ Dictionary specifying standard fields, always present and same order
    """

    fields = (
        'login',
        'avatar_url',
        'gravatar_id',
        'name',
        'company',
        'blog',
        'location',
        'email',
        'bio',
        'other_emails',
        'timezone_counts',
        'created_at',
        'updated_at')

    default_value = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields:
            if f not in self:
                self[f] = self.default_value

    def _all_fields(self):
        fields = get_fields(self)
        other_fields = tuple(
            f for f in self if f not in fields)
        return fields + other_fields

    def __str__(self, indent=''):
        fields = self._all_fields()
        field_len = max(len(f) for f in fields) + 2
        fmt = '%s{f:<%d}: {v}' % (indent, field_len)
        lines = []
        for f in fields:
            v = self[f]
            if hasattr(v, 'items'):
                lines.append(str(v))
            else:
                lines.append(fmt.format(f=f, v=v))
        return '\n'.join(lines)


def user_report(gh_user, user_df, browser=False):
    """ Report available data for `gh_user`, maybe open relevant pages

    Prints information to console.  If `browser==True` then open the user's
    Github page in the browser, and any detected Github Pages site.
    """
    if gh_user is None or gh_user.startswith('+'):
        print(f'Invalid gh_user {gh_user}')
        return
    user_data = FieldDict()
    gh_data = USER_GETTER(gh_user)
    if gh_data:
        lupdate(user_data, gh_data)
    print(user_data)
    # Get repository data
    # Add to user_data
    gh_pages = []
    for ext in ('io', 'com'):
        repo = f'{gh_user}.github.{ext}'
        try:
            GH.repository(gh_user, repo)
        except github3.exceptions.NotFoundError:
            pass
        else:
            gh_pages.append(repo)
    print('GH pages:')
    for ghp in gh_pages:
        print(f'    {ghp}')
    print('GH event emails:')
    pprint(dict(gh_user2ev_emails(gh_user).items()))
    print('Repository data')
    user_rows = user_df[user_df['gh_user'] == gh_user]
    for i in range(len(user_rows)):
        row = user_rows.iloc[i]
        repo_name = row['repo']
        print(f'For {repo_name}:')
        name = row['name']
        contribs = [c for c in REPO_GETTER.get_contributors(repo_name)
                    if c.name == name]
        assert len(contribs) == 1
        contrib = contribs[0]
        print(f'N commits: {len(contrib)}')
        print('Names:')
        print('\n'.join(contrib.names))
        print('Emails:')
        print('\n'.join(contrib.emails))
        print('Timezones:')
        print(contrib.timezone_counts)
    if browser:
        check_call(['open', f'https://github.com/{gh_user}'])
        for ghp in gh_pages:
            check_call(['open', 'https:' + gh_pages[0]])


# Read estimated Github usernames and other user data.
short_sha = '8d745da'
users = pd.read_csv(f'gh_user_map_{short_sha}.csv')

# Get location from manual input, or from Github user profiles.
users['location'] = users['gh_user'].apply(gh_user2location)
# Estimate country from the location data.  The function will print helpful
# information for missing locations or invalid countries.
users['country_code'] = users['gh_user'].apply(gh_user2country)

# Write country data to CSV
users.to_csv('users_locations.csv', index=False)
# Save cached Github user data, to save Github queries.
USER_GETTER.save_cache()

# Generate report for first user without country
# This allows me to re-run the file from IPython, to review date for users with
# missing countries, and edit the GH_USER2LOCATION data.
bads = users['country_code'].isna()
if np.any(bads):
    gh_user = users.loc[bads].iloc[0]['gh_user']
    user_report(gh_user, users, browser=True)
