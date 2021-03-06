# -*- coding: UTF-8 -*-
from coffin.shortcuts import render_to_response
from aragon.models import Budget, BudgetBreakdown, FunctionalCategory, EconomicCategory
from entities import entities_show
from helpers import *
import json


def policies(request, render_callback=None):
    # Retrieve the entity to display from the given slug
    region = Entity.objects.region()

    # Get request context
    c = get_context(request, css_class='body-entities', title=region.name)

    return entities_show(request, c, region, render_callback)


def policies_show(request, id, title, render_callback=None):
    # Get request context
    c = get_context(request, css_class='body-policies', title='')
    c['policy_uid'] = id

    # Get the budget breakdown
    c['functional_breakdown'] = BudgetBreakdown(['programme'])
    c['economic_breakdown'] = BudgetBreakdown(['chapter', 'article', 'heading'])
    c['funding_breakdown'] = BudgetBreakdown(['source', 'fund'])
    c['institutional_breakdown'] = BudgetBreakdown([_year_tagged_section, _year_tagged_department])
    get_budget_breakdown(   "fc.policy = %s and e.level = 'comunidad'", [ id ],
                            [ 
                                c['functional_breakdown'], 
                                c['economic_breakdown'],
                                c['funding_breakdown'],
                                c['institutional_breakdown']
                            ])

    # Additional data needed by the view
    show_side = 'expense'
    populate_stats(c)
    populate_descriptions(c)
    populate_years(c, 'functional_breakdown', 'comunidad')
    populate_area_descriptions(c, ['functional', 'funding', show_side])
    _populate_csv_settings(c, 'policy', id)
    _set_show_side(c, show_side)
    _set_full_breakdown(c, True)

    c['name'] = c['descriptions']['functional'].get(c['policy_uid'])
    c['title_prefix'] = c['name']

    return render(c, render_callback, 'policies/show.html')


def programmes_show(request, id, title, render_callback=None):
    # Retrieve the entity to display from the given slug
    main_entity = Entity.objects.main_entity()

    # Get request context
    c = get_context(request, css_class='body-policies', title='')
    c['programme_id'] = id
    c['programme'] = FunctionalCategory.objects.filter( budget__entity=main_entity, 
                                                        programme=id)[0]
    c['policy'] = FunctionalCategory.objects.filter(budget__entity=main_entity, 
                                                    policy=c['programme'].policy, 
                                                    function__isnull=True)[0]

    # Ignore if possible the descriptions for execution data, they are truncated and ugly
    programme_descriptions = {}
    def _populate_programme_descriptions(column_name, item):
        if not item.actual or not item.uid() in programme_descriptions:
            programme_descriptions[item.uid()] = getattr(item, 'description')

    # Get the budget breakdown.
    # The functional breakdown is an empty one, as we're at the deepest level, but since
    # we're going to be displaying this data in the policy page we send a blank one
    c['functional_breakdown'] = BudgetBreakdown([])
    c['economic_breakdown'] = BudgetBreakdown(['chapter', 'article', 'heading', 'uid'])
    c['funding_breakdown'] = BudgetBreakdown(['source', 'fund'])
    c['institutional_breakdown'] = BudgetBreakdown([_year_tagged_section, _year_tagged_department])
    get_budget_breakdown(   "fc.programme = %s and e.level = 'comunidad'", [ id ],
                            [ 
                                c['economic_breakdown'],
                                c['funding_breakdown'],
                                c['institutional_breakdown']
                            ],
                            _populate_programme_descriptions)

    # Note we don't modify the original descriptions, we're working on a copy (of the hash,
    # which is made of references to the hashes containing the descriptions themselves).
    c['descriptions'] = Budget.objects.get_all_descriptions(Entity.objects.region()).copy()
    programme_descriptions.update(c['descriptions']['expense'])
    c['descriptions']['expense'] = programme_descriptions
    c['name'] = c['descriptions']['functional'].get(c['programme_id'])
    c['title_prefix'] = c['name']

    # Additional data needed by the view
    show_side = 'expense'
    populate_stats(c)
    populate_years(c, 'institutional_breakdown', 'comunidad')
    populate_area_descriptions(c, ['functional', 'funding', show_side])
    _populate_csv_settings(c, 'programme', id)
    _set_show_side(c, show_side)
    _set_full_breakdown(c, True)

    return render(c, render_callback, 'policies/show.html')


def income_articles_show(request, id, title, render_callback=None):
    return articles_show(request, id, title, 'income', render_callback)


def expense_articles_show(request, id, title, render_callback=None):
    return articles_show(request, id, title, 'expense', render_callback)


def articles_show(request, id, title, show_side, render_callback=None):
    # Retrieve the entity to display from the given slug
    main_entity = Entity.objects.main_entity()

    # Get request context
    c = get_context(request, css_class='body-policies', title='')
    c['article_id'] = id
    c['article'] = EconomicCategory.objects.filter( budget__entity=main_entity,
                                                    article=id, 
                                                    expense=(show_side=='expense'))[0]

    # Ignore if possible the descriptions for execution data, they are truncated and ugly
    article_descriptions = {}
    def _populate_article_descriptions(column_name, item):
        if not item.actual or not item.uid() in article_descriptions:
            article_descriptions[item.uid()] = getattr(item, 'description')

    # Get the budget breakdown.
    # The functional one is used only when showing expenses.
    c['functional_breakdown'] = BudgetBreakdown(['policy', 'programme'])
    c['economic_breakdown'] = BudgetBreakdown(['heading', 'uid'])
    c['funding_breakdown'] = BudgetBreakdown(['source', 'fund'])
    c['institutional_breakdown'] = BudgetBreakdown([_year_tagged_section, _year_tagged_department])
    get_budget_breakdown(   "ec.article = %s and e.level = 'comunidad'", [ id ],
                            [ 
                                c['functional_breakdown'],
                                c['economic_breakdown'],
                                c['funding_breakdown'],
                                c['institutional_breakdown']
                            ],
                            _populate_article_descriptions)

    # Note we don't modify the original descriptions, we're working on a copy (of the hash,
    # which is made of references to the hashes containing the descriptions themselves).
    c['descriptions'] = Budget.objects.get_all_descriptions(Entity.objects.region()).copy()
    article_descriptions.update(c['descriptions'][show_side])
    c['descriptions'][show_side] = article_descriptions
    c['name'] = c['descriptions'][show_side].get(c['article_id'])
    c['title_prefix'] = c['name']

    # Additional data needed by the view
    populate_stats(c)
    populate_years(c, 'institutional_breakdown', 'comunidad')
    populate_area_descriptions(c, ['functional', 'funding', show_side])
    _populate_csv_settings(c, 'article', id)
    _set_show_side(c, show_side)
    _set_full_breakdown(c, True)

    return render(c, render_callback, 'policies/show.html')


# Unfortunately institutions id change sometimes over the years, so we need to
# use id's that are unique along time, not only inside a given budget.
def _year_tagged_section(item):
    return str(getattr(item, 'year')) + '/' + getattr(item, 'section')


def _year_tagged_department(item):
    return str(getattr(item, 'year')) + '/' + getattr(item, 'department')


def _get_tab_titles(show_side):
    if show_side == 'income':
        return {
            'economic': u"¿Cómo se ingresa?",
            'funding': u"Tipo de ingresos",
            'institutional': u"¿Quién recauda?"
        }
    else:
        return {
            'functional': u"¿En qué se gasta?",
            'economic': u"¿Cómo se gasta?",
            'funding': u"¿Cómo se financia?",
            'institutional': u"¿Quién lo gasta?"
        }

def _populate_csv_settings(c, type, id):
    c['csv_id'] = id
    c['csv_type'] = type

def _set_show_side(c, side):
    c['show_side'] = side
    c['tab_titles'] = _get_tab_titles(side)

# Do we have an exhaustive budget, classified along four dimensions? I.e. display all tabs?
def _set_full_breakdown(c, full_breakdown):
    c['full_breakdown'] = full_breakdown
