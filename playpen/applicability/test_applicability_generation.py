#!/usr/bin/env python2

from pulp.common import pic
from okaara.prompt import Prompt, COLOR_LIGHT_PURPLE, COLOR_LIGHT_BLUE
from pprint import pprint


def pause(p):
    p.prompt('Press enter to continue...', allow_empty=True)

def divider(p):
    p.write('==============================')

def title(p, text):
    p.write(text, color=COLOR_LIGHT_PURPLE)


def content_applicability1():
    consumer_criteria = { "sort": [["id", "ascending"]],
                 "filters": {"id": {"$in": ["lemonade", "sunflower", "voyager"]}}}

    options = {"consumer_criteria":consumer_criteria,
              }

    p = Prompt()
    pprint("/pulp/api/v2/consumers/actions/content/regenerate_applicability/")
    p.write('\nconsumer_criteria -', color=COLOR_LIGHT_BLUE)
    pprint(consumer_criteria)
    p.write('')
    result = pic.POST('/pulp/api/v2/consumers/actions/content/regenerate_applicability/', options)
    pause(p)
    p.write('\nresult -', color=COLOR_LIGHT_BLUE)
    pprint(result)
    p.write('')


def content_applicability2():
    repo_criteria = { "sort": [["id", "ascending"]],
                 "filters": {"id": {"$in": ["test-repo", "zoo"]}}}

    options = {"repo_criteria":repo_criteria,
              }

    p = Prompt()
    pprint("/pulp/api/v2/repositories/actions/content/regenerate_applicability/")
    p.write('\repo_criteria -', color=COLOR_LIGHT_BLUE)
    pprint(repo_criteria)
    p.write('')
    result = pic.POST('/pulp/api/v2/repositories/actions/content/regenerate_applicability/', options)
    pause(p)
    p.write('\nresult -', color=COLOR_LIGHT_BLUE)
    pprint(result)
    p.write('')


def main():
    p = Prompt()
    pic.connect()
    pic.LOG_BODIES = True

    title(p, 'Consumer Applicability Generation APIs Demo')

    pause(p)
    p.write('\n------------------------------------------------------------------------\n')

    title(p, 'Demo with consumer_criteria')
    content_applicability1()

    title(p, 'Demo with repo_criteria')
    content_applicability2()


if __name__ == '__main__':
    main()
