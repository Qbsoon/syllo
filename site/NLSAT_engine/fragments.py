from operator import sub

from z3 import *
import matplotlib.pyplot as plt

import seaborn as sns

import argparse

from nltk import *
from nltk.sem.drt import DrtParser
from nltk.sem import logic
import nltk
from nltk.sem import Expression
from nltk import load_parser
from nltk.sem import Valuation, Model
from nltk.corpus import brown

from scipy.stats import beta
from numpy import histogram


import random
import re
import time

import numpy as np
import pandas as pd


class SyllogisticTemplates:

  def __init__(self, functions):
    self.quantifiers = ["all", "exists"]
    self.functions = functions

  def template_natural_language(self, template_name):
    templates = {
        "si": "{} {} is a {}",
        "pl": "{} {} are {}",
        "si_neg": "{} {} is not a {}",
        "pl_neg": "{} {} are not {}", 
        "neg_si": "{} non-{} is a {}",
        "neg_pl": "{} non-{} are {}",
        "neg_si_neg": "{} non-{} is not a {}",
        "neg_pl_neg": "{} non-{} are not {}", 
    }

    return templates[template_name]

  def natural_language_sentence_generation(self, quantifier, variables, negations):
    det = None

    if quantifier == "all":
      if negations[variables[1]] == True :
        det = "no"
      else :
        det = random.choice(["all", "every"])
    elif quantifier == "exists":
      det = random.choice(["some", "a"])

    negs = [negations[variables[0]], negations[variables[1]]]

    sing = "pl" if det in ["all", "some", "not"] else "si"
    template_id = ""

    if negations[variables[0]] == True:
      template_id += "neg_"
    template_id += sing
    if det != "no":
      if negations[variables[1]] == True:
        template_id += "_neg"
      
    return self.template_natural_language(template_id).format(det, variables[0], variables[1])

  def generate_logic_formula(self, quantifier, predicates, negations, x, y):

    pred_func = {}
    for f in predicates :
      if negations[f] :
        pred_func[f] = Not(self.functions[f](x))
      else :
        pred_func[f] = self.functions[f](x)


    if quantifier == "all":
      fol = ForAll(x, Implies(pred_func[predicates[0]], pred_func[predicates[1]]))
    else :
      fol = Exists(x, And(pred_func[predicates[0]], pred_func[predicates[1]]))

    return fol


  def generate_sentence_logic_pair(self, nouns, verbs, x, y, negations = True):

    variables = random.sample(nouns, 2)

    if negations == True :
      negations = {variables[0] : random.choice([True, False]), 
                  variables[1] : random.choice([True, False])}

    else :
      negations = {variables[0] : False,
                   variables[1] : False}
    
    quantifier = random.choice(self.quantifiers)

    logic, sentence = None, None

    try:
      logic = self.generate_logic_formula(quantifier, variables, negations, x, y)
      sentence = self.natural_language_sentence_generation(quantifier, variables, negations)
    except :
      print(nouns, verbs, negations)
    return logic, sentence, quantifier



class RelationalSyllogiticTemplates : 

  def __init__(self, functions):
    self.quantifiers = ["all", "exists"]
    self.functions = functions

  def template_natural_language(self, template_name):
    templates = {
        "noun_verb_noun": "{} {} {} {} {}",
        "noun_verb_neg_noun": "{} {} {} {} non-{}",
        "noun_neg_verb_noun": "{} {} does not {} {} {}",
        "noun_neg_verb_neg_noun": "{} {} does not {} {} non-{}",
        "neg_noun_verb_noun": "{} non-{} {} {} {}",
        "neg_noun_verb_neg_noun": "{} non-{} {} {} non-{}",
        "neg_noun_neg_verb_noun": "{} non-{} does not {} {} {}",
        "neg_noun_neg_verb_neg_noun": "{} non-{} does not {} {} non-{}",
    }
    
    return templates[template_name]

  def quantifier_det(self, quantifier):
    det = None
    if quantifier == "all":
      det = random.choice(["all", "every"])
    elif quantifier == "exists":
      det = random.choice(["some", "a"])

    return det


  def natural_language_sentence_generation(self, quantifiers, variables, negations):
    dets = [self.quantifier_det(quantifier) for quantifier in quantifiers]

    template_id = ""

    if negations[variables[0]] == True:
      template_id += "neg_"
    template_id += "noun_"

    if negations[variables[2]] == True :
      if quantifiers[0] == "all":
        dets[0] = "no"
        if quantifiers[1] == "all":
          dets[1] = "any"
        else :
          dets[1] = "every"
      elif quantifiers[0] == "exists" and quantifiers[1] == "exists":
        dets[1] = "no"
      else :
        template_id += "neg_"
    template_id += "verb_"

    if negations[variables[1]] == True:
      template_id += "neg_"
    template_id += "noun"

      
    sentence = self.template_natural_language(template_id).format(dets[0], variables[0], variables[2], dets[1], variables[1])

    if dets[0] in ["some", "all"]:
      return sentence.replace(" does not ", " do not ")
    return sentence

  def generate_logic_formula(self, quantifiers, predicates, negations, x, y):

    pred_func = {}

    if negations[predicates[0]] :
      pred_func[predicates[0]] = Not(self.functions[predicates[0]](x))
    else :
      pred_func[predicates[0]] = self.functions[predicates[0]](x)

    if negations[predicates[1]] :
      pred_func[predicates[1]] = Not(self.functions[predicates[1]](y))
    else :
      pred_func[predicates[1]] = self.functions[predicates[1]](y)

    if negations[predicates[-1]] :
      pred_func[predicates[-1]] = Not(self.functions[predicates[-1]](x,y))
    else :
      pred_func[predicates[-1]] = self.functions[predicates[-1]](x,y)

    if quantifiers == ["all", "all"] :
      fol = ForAll(x, Implies(pred_func[predicates[0]], ForAll(y, Implies(pred_func[predicates[1]], pred_func[predicates[2]]))))
    elif quantifiers == ["all", "exists"] :
      fol = ForAll(x, Implies(pred_func[predicates[0]], Exists(y, And(pred_func[predicates[1]], pred_func[predicates[2]]))))
    elif quantifiers == ["exists", "all"] :
      fol = Exists(x, And(pred_func[predicates[0]], ForAll(y, Implies(pred_func[predicates[1]], pred_func[predicates[2]]))))
    else :
      fol = Exists(x, And(pred_func[predicates[0]], Exists(y, And(pred_func[predicates[1]], pred_func[predicates[2]]))))

    return fol


  def generate_sentence_logic_pair(self, nouns, verbs, x, y):

    binary = random.choice(verbs)
    unary = random.sample(nouns, 2)
    quantifiers = [random.choice(["all", "exists"]), random.choice(["all", "exists"])]
    negations = {unary[0] : random.choice([True, False]), 
                unary[1] : random.choice([True, False]),
                binary : random.choice([True, False])}

    variables = unary.copy()
    variables.append(binary)

    logic, sentence = None, None

    try:
      logic = self.generate_logic_formula(quantifiers, variables, negations, x, y)
      sentence = self.natural_language_sentence_generation(quantifiers, variables, negations)
    except :
      pprint(nouns, verbs, negations)
    return logic, sentence, quantifiers


class RelativeClausesTemplates:

  def __init__(self, functions):
    self.quantifiers = ["all", "exists"]
    self.functions = functions

  def template_natural_language(self, template_name):
    templates = {
      "noun_noun_si": "{} {} who is a {} is a {}",
      "noun_noun_pl": "{} {} who are {} are {}",
      "noun_neg_noun_si": "{} {} who is not a {} is a {}",
      "noun_neg_noun_pl": "{} {} who are not {} are {}",
      "noun_noun_neg_si": "{} {} who is a {} is not a {}",
      "noun_noun_neg_pl": "{} {} who are {} are not {}",
      "noun_neg_noun_neg_si": "{} {} who is not a {} is not a {}",
      "noun_neg_noun_neg_pl": "{} {} who are not {} are not {}",
      "neg_noun_noun_si": "{} non-{} who is a {} is a {}",
      "neg_noun_noun_pl": "{} non-{} who are {} are {}",
      "neg_noun_neg_noun_si": "{} non-{} who is not a {} is a {}",
      "neg_noun_neg_noun_pl": "{} non-{} who are not {} are {}",
      "neg_noun_noun_neg_si": "{} non-{} who is a {} is not a {}",
      "neg_noun_noun_neg_pl": "{} non-{} who are {} are not {}",
      "neg_noun_neg_noun_neg_si": "{} non-{} who is not a {} is not a {}",
      "neg_noun_neg_noun_neg_pl": "{} non-{} who are not {} are not {}",
    }

    return templates[template_name]

  def quantifier_det(self, quantifier):
    det = None
    if quantifier == "all":
      det = random.choice(["all", "every"])
    elif quantifier == "exists":
      det = random.choice(["some", "a"])

    return det

  def natural_language_sentence_generation(self, quantifier, variables, negations):

    det = self.quantifier_det(quantifier)

    negs = [negations[variables[0]], negations[variables[1]],negations[variables[2]]]
    sing = "pl" if det in ["all", "some"] else "si"

    template_id = ""
    if negations[variables[0]] == True :
      template_id += "neg_"

    template_id += "noun_"

    if negations[variables[1]] == True :
      template_id += "neg_"

    template_id += "noun_"


    if negations[variables[2]] == True :
      if quantifier == "all":
        det = "no"
      else :
        template_id += "neg_"

    if sing == "pl":
      template_id += "pl"
    else :
      template_id += "si"

    return self.template_natural_language(template_id).format(det, variables[0], variables[1], variables[2])

  def generate_logic_formula(self, quantifier, predicates, negations, x, y):

    pred_func = {}
    for f in predicates :
      if negations[f] :
        pred_func[f] = Not(self.functions[f](x))
      else :
        pred_func[f] = self.functions[f](x)


    if quantifier == "all":
      fol = ForAll(x, Implies(And(pred_func[predicates[0]], pred_func[predicates[1]]), pred_func[predicates[2]]))
    else :
      fol = Exists(x, And(pred_func[predicates[0]], pred_func[predicates[1]], pred_func[predicates[2]]))

    return fol


  def generate_sentence_logic_pair(self, nouns, verbs, x, y):


    variables = random.sample(nouns, 3)
    
    negations = {variables[0] : random.choice([True, False]), 
                 variables[1] : random.choice([True, False]),
                 variables[2] : random.choice([True, False])}

    
    quantifier = random.choice(self.quantifiers)
    
    logic, sentence = None, None
    try : 
      logic = self.generate_logic_formula(quantifier, variables, negations, x, y)
      sentence = self.natural_language_sentence_generation(quantifier, variables, negations)
    except :
      print(nouns, verbs, negations)

    return logic, sentence, quantifier


class RelativeTVTemplates:
  def __init__(self, functions):
    self.quantifiers = ["all", "exists"]
    self.functions = functions

  def template_natural_language(self, template_name, sub_obj_type):
    if sub_obj_type == "subject":
      templates = {
          "2q_n_v_n_noun_si": "{} {} who {} {} {} is a {}",
          "2q_n_v_n_noun_pl": "{} {} who {} {} {} are {}",
          "2q_n_v_n_noun_neg_si": "{} {} who {} {} {} is not a {}",
          "2q_n_v_n_noun_neg_pl": "{} {} who {} {} {} are not {}",
          "2q_n_v_n_neg_noun_si": "{} {} who {} {} non-{} is a {}",
          "2q_n_v_n_neg_noun_pl": "{} {} who {} {} non-{} are {}",
          "2q_n_v_n_neg_noun_neg_si": "{} {} who {} {} non-{} is not a {}",
          "2q_n_v_n_neg_noun_neg_pl": "{} {} who {} {} non-{} are not {}",
          "2q_n_v_neg_n_noun_si": "{} {} who does not {} {} {} is a {}",
          "2q_n_v_neg_n_noun_pl": "{} {} who do not {} {} {} are {}",
          "2q_n_v_neg_n_noun_neg_si": "{} {} who does not {} {} {} is not a {}",
          "2q_n_v_neg_n_noun_neg_pl": "{} {} who do not {} {} {} are not {}",
          "2q_n_v_neg_n_neg_noun_si": "{} {} who does not {} {} non-{} is a {}",
          "2q_n_v_neg_n_neg_noun_pl": "{} {} who do not {} {} non-{} are {}",
          "2q_n_v_neg_n_neg_noun_neg_si": "{} {} who does not {} {} non-{} is not a {}",
          "2q_n_v_neg_n_neg_noun_neg_pl": "{} {} who do not {} {} non-{} are not {}",
          "2q_n_neg_v_n_noun_si": "{} non-{} who {} {} {} is a {}",
          "2q_n_neg_v_n_noun_pl": "{} non-{} who {} {} {} are {}",
          "2q_n_neg_v_n_noun_neg_si": "{} non-{} who {} {} {} is not a {}",
          "2q_n_neg_v_n_noun_neg_pl": "{} non-{} who {} {} {} are not {}",
          "2q_n_neg_v_n_neg_noun_si": "{} non-{} who {} {} non-{} is a {}",
          "2q_n_neg_v_n_neg_noun_pl": "{} non-{} who {} {} non-{} are {}",
          "2q_n_neg_v_n_neg_noun_neg_si": "{} non-{} who {} {} non-{} is not a {}",
          "2q_n_neg_v_n_neg_noun_neg_pl": "{} non-{} who {} {} non-{} are not {}",
          "2q_n_neg_v_neg_n_noun_si": "{} non-{} who does not {} {} {} is a {}",
          "2q_n_neg_v_neg_n_noun_pl": "{} non-{} who do not {} {} {} are {}",
          "2q_n_neg_v_neg_n_noun_neg_si": "{} non-{} who does not {} {} {} is not a {}",
          "2q_n_neg_v_neg_n_noun_neg_pl": "{} non-{} who do not {} {} {} are not {}",
          "2q_n_neg_v_neg_n_neg_noun_si": "{} non-{} who does not {} {} non-{} is a {}",
          "2q_n_neg_v_neg_n_neg_noun_pl": "{} non-{} who do not {} {} non-{} are {}",
          "2q_n_neg_v_neg_n_neg_noun_neg_si": "{} non-{} who does not {} {} non-{} is not a {}",
          "2q_n_neg_v_neg_n_neg_noun_neg_pl": "{} non-{} who do not {} {} non-{} are not {}",
      }

      return templates[template_name]

    if sub_obj_type == "object":
      templates = {
          "2q_n_v_n_noun_si": "{} {} {} {} {} who is a {}",
          "2q_n_v_n_noun_pl": "{} {} {} {} {} who are {}",
          "2q_n_v_n_noun_neg_si": "{} {} {} {} {} who is not a {}",
          "2q_n_v_n_noun_neg_pl": "{} {} {} {} {} who are not {}",
          "2q_n_v_n_neg_noun_si": "{} {} {} {} non-{} who is a {}",
          "2q_n_v_n_neg_noun_pl": "{} {} {} {} non-{} who are {}",
          "2q_n_v_n_neg_noun_neg_si": "{} {} {} {} non-{} who is not a {}",
          "2q_n_v_n_neg_noun_neg_pl": "{} {} {} {} non-{} who are not {}",
          "2q_n_v_neg_n_noun_si": "{} {} does not {} {} {} who is a {}",
          "2q_n_v_neg_n_noun_pl": "{} {} do not {} {} {} who are {}",
          "2q_n_v_neg_n_noun_neg_si": "{} {} does not {} {} {} who is not a {}",
          "2q_n_v_neg_n_noun_neg_pl": "{} {} do not {} {} {} who are not {}",
          "2q_n_v_neg_n_neg_noun_si": "{} {} does not {} {} non-{} who is a {}",
          "2q_n_v_neg_n_neg_noun_pl": "{} {} do not {} {} non-{} who are {}",
          "2q_n_v_neg_n_neg_noun_neg_si": "{} {} does not {} {} non-{} who is not a {}",
          "2q_n_v_neg_n_neg_noun_neg_pl": "{} {} do not {} {} non-{} who are not {}",
          "2q_n_neg_v_n_noun_si": "{} non-{} {} {} {} who is a {}",
          "2q_n_neg_v_n_noun_pl": "{} non-{} {} {} {} who are {}",
          "2q_n_neg_v_n_noun_neg_si": "{} non-{} {} {} {} who is not a {}",
          "2q_n_neg_v_n_noun_neg_pl": "{} non-{} {} {} {} who are not {}",
          "2q_n_neg_v_n_neg_noun_si": "{} non-{} {} {} non-{} who is a {}",
          "2q_n_neg_v_n_neg_noun_pl": "{} non-{} {} {} non-{} who are {}",
          "2q_n_neg_v_n_neg_noun_neg_si": "{} non-{} {} {} non-{} who is not a {}",
          "2q_n_neg_v_n_neg_noun_neg_pl": "{} non-{} {} {} non-{} who are not {}",
          "2q_n_neg_v_neg_n_noun_si": "{} non-{} does not {} {} {} who is a {}",
          "2q_n_neg_v_neg_n_noun_pl": "{} non-{} do not {} {} {} who are {}",
          "2q_n_neg_v_neg_n_noun_neg_si": "{} non-{} does not {} {} {} who is not a {}",
          "2q_n_neg_v_neg_n_noun_neg_pl": "{} non-{} do not {} {} {} who are not {}",
          "2q_n_neg_v_neg_n_neg_noun_si": "{} non-{} does not {} {} non-{} who is a {}",
          "2q_n_neg_v_neg_n_neg_noun_pl": "{} non-{} do not {} {} non-{} who are {}",
          "2q_n_neg_v_neg_n_neg_noun_neg_si": "{} non-{} does not {} {} non-{} who is not a {}",
          "2q_n_neg_v_neg_n_neg_noun_neg_pl": "{} non-{} do not {} {} non-{} who are not {}",
      }

      return templates[template_name]

  def quantifier_det(self, quantifier):
    det = None
    if quantifier == "all":
      det = random.choice(["all", "every"])
    elif quantifier == "exists":
      det = random.choice(["some", "a"])

    return det


  def natural_language_sentence_generation(self, quantifiers, variables, negations, sub_obj_type = "subject"):
    if sub_obj_type == "subject":
      dets = None
      template_id = "2q_n_"
      dets = [self.quantifier_det(quantifiers[0]), self.quantifier_det(quantifiers[1])]
      if negations[variables[0]] == True:
        template_id += "neg_"

      template_id += "v_"
      if negations[variables[3]] == True:
        if quantifiers[1] == "all":
          dets[1] = "no"
        else :
          template_id += "neg_"
      
      template_id += "n_" 
      if negations[variables[1]] == True:
        template_id += "neg_"
      
      template_id += "noun_"
      if negations[variables[2]] == True:
        if quantifiers[0] == "all" and dets[1] != "no":
          dets[0] = "no"
        else :
          template_id += "neg_"

      template_id += "pl" if dets[0] in ["all", "some"] else "si"
      return self.template_natural_language(template_id,sub_obj_type).format(dets[0], variables[0], variables[3], dets[1], variables[1], variables[2])
          
    elif sub_obj_type == "object":
      template_id = "2q_n_"
      dets = [self.quantifier_det(quantifiers[0]), self.quantifier_det(quantifiers[1])]
      if negations[variables[0]] == True:
        template_id += "neg_"

      template_id += "v_"
      if negations[variables[3]] == True:
        if quantifiers[0] == "all":
          dets[0] = "no"
          if quantifiers[1] == "exists":
            dets[1] = "every"
          else :
            dets[1] = "any"
        else :
          template_id += "neg_"

      
      template_id += "n_" 
      if negations[variables[1]] == True:
        template_id += "neg_"
      
      template_id += "noun_"
      if negations[variables[2]] == True:
        template_id += "neg_"

      template_id += "pl" if dets[0] in ["all", "some"] else "si"
      return self.template_natural_language(template_id, sub_obj_type).format(dets[0], variables[0], variables[3], dets[1], variables[1], variables[2])
    

  def generate_logic_formula(self, quantifiers, predicates, negations, x, y, sub_obj_type = "subject"):

    pred_func = {}

    if negations[predicates[0]] :
      pred_func[predicates[0]] = Not(self.functions[predicates[0]](x))
    else :
      pred_func[predicates[0]] = self.functions[predicates[0]](x)

    if negations[predicates[1]] :
      pred_func[predicates[1]] = Not(self.functions[predicates[1]](y))
    else :
      pred_func[predicates[1]] = self.functions[predicates[1]](y)

    if negations[predicates[2]] :
      if sub_obj_type == "subject":
        pred_func[predicates[2]] = Not(self.functions[predicates[2]](x))
      else :
        pred_func[predicates[2]] = Not(self.functions[predicates[2]](y))
    else :
      if sub_obj_type == "subject":
        pred_func[predicates[2]] = self.functions[predicates[2]](x)
      else :
        pred_func[predicates[2]] = self.functions[predicates[2]](y)

    if negations[predicates[-1]] :
      pred_func[predicates[-1]] = Not(self.functions[predicates[-1]](x,y))
    else :
      pred_func[predicates[-1]] = self.functions[predicates[-1]](x,y)


    if sub_obj_type == "subject":
      if quantifiers == ["all", "all"] :
        fol = ForAll(x, Implies(And(pred_func[predicates[0]], ForAll(y, Implies(pred_func[predicates[1]], pred_func[predicates[3]]))), pred_func[predicates[2]]))
      elif quantifiers == ["all", "exists"] :
        fol = ForAll(x, Implies(And(pred_func[predicates[0]], Exists(y, And(pred_func[predicates[1]], pred_func[predicates[3]]))), pred_func[predicates[2]]))
      elif quantifiers == ["exists", "all"] :
        fol = Exists(x, And(And(pred_func[predicates[0]], ForAll(y, Implies(pred_func[predicates[1]], pred_func[predicates[3]]))), pred_func[predicates[2]]))
      else :
        fol = Exists(x, And(And(pred_func[predicates[0]], Exists(y, And(pred_func[predicates[1]], pred_func[predicates[3]]))), pred_func[predicates[2]]))
    else :
      if quantifiers == ["all", "all"] :
        fol = ForAll(x, Implies(pred_func[predicates[0]], ForAll(y, Implies(And(pred_func[predicates[1]], pred_func[predicates[2]]), pred_func[predicates[3]]))))
      elif quantifiers == ["all", "exists"] :
        fol = ForAll(x, Implies(pred_func[predicates[0]], Exists(y, And(And(pred_func[predicates[1]], pred_func[predicates[2]]), pred_func[predicates[3]]))))
      elif quantifiers == ["exists", "all"] :
        fol = Exists(x, And(pred_func[predicates[0]], ForAll(y, Implies(And(pred_func[predicates[1]], pred_func[predicates[2]]), pred_func[predicates[3]]))))
      else :
        fol = Exists(x, And(pred_func[predicates[0]], Exists(y, And(And(pred_func[predicates[1]], pred_func[predicates[2]]), pred_func[predicates[3]]))))
    return fol


  def generate_sentence_logic_pair(self, nouns, verbs, x, y):

    binary = random.choice(verbs)
    unary = random.sample(nouns, 3)
    quantifiers = [random.choice(["all", "exists"]), random.choice(["all", "exists"])]
    sub_obj_type = random.choice(["subject", "object"])
    negations = {unary[0] : random.choice([True, False]), 
                 unary[1] : random.choice([True, False]),
                 unary[2] : random.choice([True, False]), 
                 binary : random.choice([True, False])}

    variables = unary.copy()
    variables.append(binary)

    logic, sentence = None, None
    try :
      logic = self.generate_logic_formula(quantifiers, variables, negations, x, y, sub_obj_type)
      sentence = self.natural_language_sentence_generation(quantifiers, variables, negations, sub_obj_type)
    except :
      print(nouns, verbs, negations, sub_obj_type)
    return logic, sentence, quantifiers

class AnaphoraTemplates:
  def __init__(self, functions):
    self.quantifiers = ["all", "exists"]
    self.functions = functions

  def template_natural_language(self, template_name):
    templates = {
        "2q_n_v_n_v_si_si": "{} {} {} {} {} who {} {}",
        "2q_n_v_n_v_si_pl": "{} {} {} {} {} who {} {}",
        "2q_n_v_n_v_pl_si": "{} {} {} {} {} who {} {}",
        "2q_n_v_n_v_pl_pl": "{} {} {} {} {} who {} {}",
        "2q_n_v_n_v_neg_si_si": "{} {} {} {} {} who does not {} {}",
        "2q_n_v_n_v_neg_si_pl": "{} {} {} {} {} who do not {} {}",
        "2q_n_v_n_v_neg_pl_si": "{} {} {} {} {} who does not {} {}",
        "2q_n_v_n_v_neg_pl_pl": "{} {} {} {} {} who do not {} {}",
        "2q_n_v_neg_n_v_si_si": "{} {} does not {} {} {} who {} {}",
        "2q_n_v_neg_n_v_pl_si": "{} {} do not {} {} {} who {} {}",
        "2q_n_v_neg_n_v_si_pl": "{} {} does not {} {} {} who {} {}",
        "2q_n_v_neg_n_v_pl_pl": "{} {} do not {} {} {} who {} {}",
        "2q_n_v_neg_n_v_neg_si_si": "{} {} does not {} {} {} who does not {} {}",
        "2q_n_v_neg_n_v_neg_si_pl": "{} {} does not {} {} {} who do not {} {}",
        "2q_n_v_neg_n_v_neg_pl_si": "{} {} do not {} {} {} who does not {} {}",
        "2q_n_v_neg_n_v_neg_pl_pl": "{} {} do not {} {} {} who do not {} {}",
        "2q_n_v_n_neg_v_si_si": "{} {} {} {} non-{} who {} {}",
        "2q_n_v_n_neg_v_si_pl": "{} {} {} {} non-{} who {} {}",
        "2q_n_v_n_neg_v_pl_si": "{} {} {} {} non-{} who {} {}",
        "2q_n_v_n_neg_v_pl_pl": "{} {} {} {} non-{} who {} {}",
        "2q_n_v_n_neg_v_neg_si_si": "{} {} {} {} non-{} who does not {} {}",
        "2q_n_v_n_neg_v_neg_si_pl": "{} {} {} {} non-{} who do not {} {}",
        "2q_n_v_n_neg_v_neg_pl_si": "{} {} {} {} non-{} who does not {} {}",
        "2q_n_v_n_neg_v_neg_pl_pl": "{} {} {} {} non-{} who do not {} {}",
        "2q_n_v_neg_n_neg_v_si_si": "{} {} does not {} {} non-{} who {} {}",
        "2q_n_v_neg_n_neg_v_pl_si": "{} {} do not {} {} non-{} who {} {}",
        "2q_n_v_neg_n_neg_v_si_pl": "{} {} does not {} {} non-{} who {} {}",
        "2q_n_v_neg_n_neg_v_pl_pl": "{} {} do not {} {} non-{} who {} {}",
        "2q_n_v_neg_n_neg_v_neg_si_si": "{} {} does not {} {} non-{} who does not {} {}",
        "2q_n_v_neg_n_neg_v_neg_si_pl": "{} {} does not {} {} non-{} who do not {} {}",
        "2q_n_v_neg_n_neg_v_neg_pl_si": "{} {} do not {} {} non-{} who does not {} {}",
        "2q_n_v_neg_n_neg_v_neg_pl_pl": "{} {} do not {} {} non-{} who do not {} {}",
        "2q_n_neg_v_n_v_si_si": "{} non-{} {} {} {} who {} {}",
        "2q_n_neg_v_n_v_si_pl": "{} non-{} {} {} {} who {} {}",
        "2q_n_neg_v_n_v_pl_si": "{} non-{} {} {} {} who {} {}",
        "2q_n_neg_v_n_v_pl_pl": "{} non-{} {} {} {} who {} {}",
        "2q_n_neg_v_n_v_neg_si_si": "{} non-{} {} {} {} who does not {} {}",
        "2q_n_neg_v_n_v_neg_si_pl": "{} non-{} {} {} {} who do not {} {}",
        "2q_n_neg_v_n_v_neg_pl_si": "{} non-{} {} {} {} who does not {} {}",
        "2q_n_neg_v_n_v_neg_pl_pl": "{} non-{} {} {} {} who do not {} {}",
        "2q_n_neg_v_neg_n_v_si_si": "{} non-{} does not {} {} {} who {} {}",
        "2q_n_neg_v_neg_n_v_si_pl": "{} non-{} does not {} {} {} who {} {}",
        "2q_n_neg_v_neg_n_v_pl_si": "{} non-{} do not {} {} {} who {} {}",
        "2q_n_neg_v_neg_n_v_pl_pl": "{} non-{} do not {} {} {} who {} {}",
        "2q_n_neg_v_neg_n_v_neg_si_si": "{} non-{} does not {} {} {} who does not {} {}",
        "2q_n_neg_v_neg_n_v_neg_si_pl": "{} non-{} does not {} {} {} who do not {} {}",
        "2q_n_neg_v_neg_n_v_neg_pl_si": "{} non-{} do not {} {} {} who does not {} {}",
        "2q_n_neg_v_neg_n_v_neg_pl_pl": "{} non-{} do not {} {} {} who do not {} {}",
        "2q_n_neg_v_n_neg_v_si_si": "{} non-{} {} {} non-{} who {} {}",
        "2q_n_neg_v_n_neg_v_si_pl": "{} non-{} {} {} non-{} who {} {}",
        "2q_n_neg_v_n_neg_v_pl_si": "{} non-{} {} {} non-{} who {} {}",
        "2q_n_neg_v_n_neg_v_pl_pl": "{} non-{} {} {} non-{} who {} {}",
        "2q_n_neg_v_n_neg_v_neg_si_si": "{} non-{} {} {} non-{} who does not {} {}",
        "2q_n_neg_v_n_neg_v_neg_si_pl": "{} non-{} {} {} non-{} who do not {} {}",
        "2q_n_neg_v_n_neg_v_neg_pl_si": "{} non-{} {} {} non-{} who does not {} {}",
        "2q_n_neg_v_n_neg_v_neg_pl_pl": "{} non-{} {} {} non-{} who do not {} {}",
        "2q_n_neg_v_neg_n_neg_v_si_si": "{} non-{} does not {} {} non-{} who {} {}",
        "2q_n_neg_v_neg_n_neg_v_si_pl": "{} non-{} does not {} {} non-{} who {} {}",
        "2q_n_neg_v_neg_n_neg_v_pl_si": "{} non-{} do not {} {} non-{} who {} {}",
        "2q_n_neg_v_neg_n_neg_v_pl_pl": "{} non-{} do not {} {} non-{} who {} {}",
        "2q_n_neg_v_neg_n_neg_v_neg_si_si": "{} non-{} does not {} {} non-{} who does not {} {}",
        "2q_n_neg_v_neg_n_neg_v_neg_si_pl": "{} non-{} does not {} {} non-{} who do not {} {}",
        "2q_n_neg_v_neg_n_neg_v_neg_pl_si": "{} non-{} do not {} {} non-{} who does not {} {}",
        "2q_n_neg_v_neg_n_neg_v_neg_pl_pl": "{} non-{} do not {} {} non-{} who do not {} {}"
      }

    return templates[template_name]

  def quantifier_det(self, quantifier):
    det = None
    if quantifier == "all":
      det = random.choice(["all", "every"])
    elif quantifier == "exists":
      det = random.choice(["some", "a"])

    return det


  def natural_language_sentence_generation(self, quantifiers, variables, negations):
    dets = [self.quantifier_det(quantifiers[0]), self.quantifier_det(quantifiers[1])]
    template_id = "2q_n_"

    if negations[variables[0]] == True:
      template_id += "neg_"
    template_id += "v_"
    if negations[variables[3]] == True:
      if quantifiers[0] == "all":
        dets[0] = "no"
        if quantifiers[1] == "all":
          dets[1] = "any"
        else :
          dets[1] = "every"
      elif (quantifiers[0] == "exists") and (quantifiers[1] == "exists"):
        dets[1] = "no"
      else :
        template_id += "neg_"
    template_id += "n_"
    if negations[variables[1]] == True:
      template_id += "neg_"
    template_id += "v_"
    if negations[variables[2]] == True:
      template_id += "neg_"
    
    if dets[0] in ["all", "some"]:
      template_id += "pl_"
      pronoun = "them"
    else :
      template_id += "si_"
      pronoun = random.choice(["him", "her"])
    
    if dets[1] in ["all", "some"]:
      template_id += "pl"
    else :
      template_id += "si"


    return self.template_natural_language(template_id).format(dets[0], variables[0], variables[3], dets[1], variables[1], variables[2], pronoun)

    

  def generate_logic_formula(self, quantifiers, predicates, negations, x, y):

    pred_func = {}

    if negations[predicates[0]] :
      pred_func[predicates[0]] = Not(self.functions[predicates[0]](x))
    else :
      pred_func[predicates[0]] = self.functions[predicates[0]](x)

    if negations[predicates[1]] :
      pred_func[predicates[1]] = Not(self.functions[predicates[1]](y))
    else :
      pred_func[predicates[1]] = self.functions[predicates[1]](y)

    if negations[predicates[2]] :
      pred_func[predicates[2]] = Not(self.functions[predicates[2]](y,x))
    else :
      pred_func[predicates[2]] = self.functions[predicates[2]](y,x)
    
    if negations[predicates[-1]] :
      pred_func[predicates[-1]] = Not(self.functions[predicates[-1]](x,y))
    else :
      pred_func[predicates[-1]] = self.functions[predicates[-1]](x,y)

    if quantifiers == ["all", "all"] :
      fol = ForAll(x, Implies(pred_func[predicates[0]], ForAll(y, Implies(And(pred_func[predicates[1]], pred_func[predicates[2]]), pred_func[predicates[3]]))))
    elif quantifiers == ["all", "exists"] :
      fol = ForAll(x, Implies(pred_func[predicates[0]], Exists(y, And(And(pred_func[predicates[1]], pred_func[predicates[2]]), pred_func[predicates[3]]))))
    elif quantifiers == ["exists", "all"] :
      fol = Exists(x, And(pred_func[predicates[0]], ForAll(y, Implies(And(pred_func[predicates[1]], pred_func[predicates[2]]), pred_func[predicates[3]]))))
    else :
      fol = Exists(x, And(pred_func[predicates[0]], Exists(y, And(And(pred_func[predicates[1]], pred_func[predicates[2]]), pred_func[predicates[3]]))))
    return fol


  def generate_sentence_logic_pair(self, nouns, verbs, x, y):

    binary = random.sample(verbs, 2)
    unary = random.sample(nouns, 2)
    quantifiers = [random.choice(["all", "exists"]), random.choice(["all", "exists"])]

    negations = {unary[0] : random.choice([True, False]), 
                 unary[1] : random.choice([True, False]),
                 binary[0] : random.choice([True, False]), 
                 binary[1] : random.choice([True, False])}

    variables = unary.copy()
    variables.extend(binary)

    logic, sentence = None, None

    logic = self.generate_logic_formula(quantifiers, variables, negations, x, y)
    sentence = self.natural_language_sentence_generation(quantifiers, variables, negations)

    return logic, sentence, quantifiers
    

    