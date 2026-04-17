# ---------------------------------------------------------------------------
# Modified by nestivi
# Modifications: Added a Polish language lexicon, implemented dynamic 
# grammatical inflection, and adapted the logic to support double negation.
# Original code licensed under the Apache License, Version 2.0.
# ---------------------------------------------------------------------------

import random
from z3 import *
from pprint import pprint

class SyllogisticTemplates:

  def __init__(self, functions, lexicon):
    self.quantifiers = ["all", "exists"]
    self.functions = functions
    self.lexicon = lexicon

  def template_natural_language(self, template_name):
    templates = {
        "si": "{} {} jest {}",
        "pl": "{} {} są {}",
        "si_neg": "{} {} nie jest {}",
        "pl_neg": "{} {} nie są {}", 
        "neg_si": "{} nie-{} jest {}",
        "neg_pl": "{} nie-{} są {}",
        "neg_si_neg": "{} nie-{} nie jest {}",
        "neg_pl_neg": "{} nie-{} nie są {}", 
    }
    return templates[template_name]

  def natural_language_sentence_generation(self, quantifier, variables, negations):
    det = None
    if quantifier == "all":
      if negations[variables[1]] == True :
        det = "żaden"
      else :
        det = random.choice(["każdy", "każdy"])
    elif quantifier == "exists":
      det = random.choice(["pewien", "jakiś"])

    template_id = ""
    if negations[variables[0]] == True:
      template_id += "neg_"

    template_id += "si"
    
    if negations[variables[1]] == True:
      template_id += "_neg"
      
    subj = self.lexicon[variables[0]]["M"]
    obj = self.lexicon[variables[1]]["N"]

    return self.template_natural_language(template_id).format(det, subj, obj)

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

  def __init__(self, functions, lexicon):
    self.quantifiers = ["all", "exists"]
    self.functions = functions
    self.lexicon = lexicon

  def template_natural_language(self, template_name):
    templates = {
        "noun_verb_noun": "{} {} {} {} {}",
        "noun_verb_neg_noun": "{} {} {} {} nie-{}",
        "noun_neg_verb_noun": "{} {} nie {} {} {}",
        "noun_neg_verb_neg_noun": "{} {} nie {} {} nie-{}",
        "neg_noun_verb_noun": "{} nie-{} {} {} {}",
        "neg_noun_verb_neg_noun": "{} nie-{} {} {} nie-{}",
        "neg_noun_neg_verb_noun": "{} nie-{} nie {} {} {}",
        "neg_noun_neg_verb_neg_noun": "{} nie-{} nie {} {} nie-{}",
    }
    return templates[template_name]

  def quantifier_det(self, quantifier):
    det = None
    if quantifier == "all":
      det = random.choice(["każdy", "każdy"])
    elif quantifier == "exists":
      det = random.choice(["pewien", "jakiś"])
    return det

  def natural_language_sentence_generation(self, quantifiers, variables, negations):
    dets = [self.quantifier_det(quantifiers[0]), self.quantifier_det(quantifiers[1])]

    template_id = ""
    if negations[variables[0]] == True:
      template_id += "neg_"
    template_id += "noun_"

    if negations[variables[2]] == True :
      template_id += "neg_"
      if quantifiers[0] == "all":
        dets[0] = "żaden"
        if quantifiers[1] == "all":
          dets[1] = "żaden"
        else :
          dets[1] = "każdy"
      elif quantifiers[0] == "exists" and quantifiers[1] == "exists":
        dets[1] = "żaden"
      
    template_id += "verb_"
    if negations[variables[1]] == True:
      template_id += "neg_"
    template_id += "noun"

    # ODMIANA SŁÓW:
    subj = self.lexicon[variables[0]]["M"] # Podmiot
    verb = self.lexicon[variables[2]]["si"] # Czasownik
    
    # Odmiana kwantyfikatora obiektu (dets[1])
    det_obj = dets[1]
    if det_obj == "każdy":
        det_obj = "każdego"
    elif det_obj == "żaden":
        det_obj = "żadnego"
    elif det_obj in ["pewien", "jakiś"]:
        det_obj = "pewnego"
        
    if dets[0] == "żaden" and negations[variables[2]]:
        det_obj = "żadnego"
    
    # Obiekt 
    if negations[variables[2]] == True:
        obj = self.lexicon[variables[1]]["D"]
    else:
        obj = self.lexicon[variables[1]]["B"]
      
    sentence = self.template_natural_language(template_id).format(dets[0], subj, verb, det_obj, obj)

    if dets[0] in ["pewien", "każdy"]:
      return sentence.replace(" nie ", " nie ")
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

  def __init__(self, functions, lexicon):
    self.quantifiers = ["all", "exists"]
    self.functions = functions
    self.lexicon = lexicon

  def template_natural_language(self, template_name):
    templates = {
      "noun_noun_si": "{} {} który jest {} jest {}",
      "noun_noun_pl": "{} {} którzy są {} są {}",
      "noun_neg_noun_si": "{} {} który nie jest {} jest {}",
      "noun_neg_noun_pl": "{} {} którzy nie są {} są {}",
      "noun_noun_neg_si": "{} {} który jest {} nie jest {}",
      "noun_noun_neg_pl": "{} {} którzy są {} nie są {}",
      "noun_neg_noun_neg_si": "{} {} który nie jest {} nie jest {}",
      "noun_neg_noun_neg_pl": "{} {} którzy nie są {} nie są {}",
      "neg_noun_noun_si": "{} nie-{} który jest {} jest {}",
      "neg_noun_noun_pl": "{} nie-{} którzy są {} są {}",
      "neg_noun_neg_noun_si": "{} nie-{} który nie jest {} jest {}",
      "neg_noun_neg_noun_pl": "{} nie-{} którzy nie są {} są {}",
      "neg_noun_noun_neg_si": "{} nie-{} który jest {} nie jest {}",
      "neg_noun_noun_neg_pl": "{} nie-{} którzy są {} nie są {}",
      "neg_noun_neg_noun_neg_si": "{} nie-{} który nie jest {} nie jest {}",
      "neg_noun_neg_noun_neg_pl": "{} nie-{} którzy nie są {} nie są {}",
    }
    return templates[template_name]

  def quantifier_det(self, quantifier):
    det = None
    if quantifier == "all":
      det = random.choice(["każdy", "każdy"])
    elif quantifier == "exists":
      det = random.choice(["pewien", "jakiś"])
    return det

  def natural_language_sentence_generation(self, quantifier, variables, negations):
    det = self.quantifier_det(quantifier)
    template_id = ""
    if negations[variables[0]] == True :
      template_id += "neg_"
    template_id += "noun_"

    if negations[variables[1]] == True :
      template_id += "neg_"
    template_id += "noun_"

    if negations[variables[2]] == True :
      template_id += "neg_"
      if quantifier == "all":
        det = "żaden"

    template_id += "si"

    # ODMIANA:
    subj = self.lexicon[variables[0]]["M"]
    obj1 = self.lexicon[variables[1]]["N"] # po 'jest' w zdaniu względnym
    obj2 = self.lexicon[variables[2]]["N"] # po 'jest' głównym

    return self.template_natural_language(template_id).format(det, subj, obj1, obj2)

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
  def __init__(self, functions, lexicon):
    self.quantifiers = ["all", "exists"]
    self.functions = functions
    self.lexicon = lexicon

  def template_natural_language(self, template_name, sub_obj_type):
    if sub_obj_type == "subject":
      templates = {
          "2q_n_v_n_noun_si": "{} {} który {} {} {} jest {}",
          "2q_n_v_n_noun_pl": "{} {} którzy {} {} {} są {}",
          "2q_n_v_n_noun_neg_si": "{} {} który {} {} {} nie jest {}",
          "2q_n_v_n_noun_neg_pl": "{} {} którzy {} {} {} nie są {}",
          "2q_n_v_n_neg_noun_si": "{} {} który {} {} nie-{} jest {}",
          "2q_n_v_n_neg_noun_pl": "{} {} którzy {} {} nie-{} są {}",
          "2q_n_v_n_neg_noun_neg_si": "{} {} który {} {} nie-{} nie jest {}",
          "2q_n_v_n_neg_noun_neg_pl": "{} {} którzy {} {} nie-{} nie są {}",
          "2q_n_v_neg_n_noun_si": "{} {} który nie {} {} {} jest {}",
          "2q_n_v_neg_n_noun_pl": "{} {} którzy nie {} {} {} są {}",
          "2q_n_v_neg_n_noun_neg_si": "{} {} który nie {} {} {} nie jest {}",
          "2q_n_v_neg_n_noun_neg_pl": "{} {} którzy nie {} {} {} nie są {}",
          "2q_n_v_neg_n_neg_noun_si": "{} {} który nie {} {} nie-{} jest {}",
          "2q_n_v_neg_n_neg_noun_pl": "{} {} którzy nie {} {} nie-{} są {}",
          "2q_n_v_neg_n_neg_noun_neg_si": "{} {} który nie {} {} nie-{} nie jest {}",
          "2q_n_v_neg_n_neg_noun_neg_pl": "{} {} którzy nie {} {} nie-{} nie są {}",
          "2q_n_neg_v_n_noun_si": "{} nie-{} który {} {} {} jest {}",
          "2q_n_neg_v_n_noun_pl": "{} nie-{} którzy {} {} {} są {}",
          "2q_n_neg_v_n_noun_neg_si": "{} nie-{} który {} {} {} nie jest {}",
          "2q_n_neg_v_n_noun_neg_pl": "{} nie-{} którzy {} {} {} nie są {}",
          "2q_n_neg_v_n_neg_noun_si": "{} nie-{} który {} {} nie-{} jest {}",
          "2q_n_neg_v_n_neg_noun_pl": "{} nie-{} którzy {} {} nie-{} są {}",
          "2q_n_neg_v_n_neg_noun_neg_si": "{} nie-{} który {} {} nie-{} nie jest {}",
          "2q_n_neg_v_n_neg_noun_neg_pl": "{} nie-{} którzy {} {} nie-{} nie są {}",
          "2q_n_neg_v_neg_n_noun_si": "{} nie-{} który nie {} {} {} jest {}",
          "2q_n_neg_v_neg_n_noun_pl": "{} nie-{} którzy nie {} {} {} są {}",
          "2q_n_neg_v_neg_n_noun_neg_si": "{} nie-{} który nie {} {} {} nie jest {}",
          "2q_n_neg_v_neg_n_noun_neg_pl": "{} nie-{} którzy nie {} {} {} nie są {}",
          "2q_n_neg_v_neg_n_neg_noun_si": "{} nie-{} który nie {} {} nie-{} jest {}",
          "2q_n_neg_v_neg_n_neg_noun_pl": "{} nie-{} którzy nie {} {} nie-{} są {}",
          "2q_n_neg_v_neg_n_neg_noun_neg_si": "{} nie-{} który nie {} {} nie-{} nie jest {}",
          "2q_n_neg_v_neg_n_neg_noun_neg_pl": "{} nie-{} którzy nie {} {} nie-{} nie są {}",
      }
      return templates[template_name]

    if sub_obj_type == "object":
      templates = {
          "2q_n_v_n_noun_si": "{} {} {} {} {} który jest {}",
          "2q_n_v_n_noun_pl": "{} {} {} {} {} którzy są {}",
          "2q_n_v_n_noun_neg_si": "{} {} {} {} {} który nie jest {}",
          "2q_n_v_n_noun_neg_pl": "{} {} {} {} {} którzy nie są {}",
          "2q_n_v_n_neg_noun_si": "{} {} {} {} nie-{} który jest {}",
          "2q_n_v_n_neg_noun_pl": "{} {} {} {} nie-{} którzy są {}",
          "2q_n_v_n_neg_noun_neg_si": "{} {} {} {} nie-{} który nie jest {}",
          "2q_n_v_n_neg_noun_neg_pl": "{} {} {} {} nie-{} którzy nie są {}",
          "2q_n_v_neg_n_noun_si": "{} {} nie {} {} {} który jest {}",
          "2q_n_v_neg_n_noun_pl": "{} {} nie {} {} {} którzy są {}",
          "2q_n_v_neg_n_noun_neg_si": "{} {} nie {} {} {} który nie jest {}",
          "2q_n_v_neg_n_noun_neg_pl": "{} {} nie {} {} {} którzy nie są {}",
          "2q_n_v_neg_n_neg_noun_si": "{} {} nie {} {} nie-{} który jest {}",
          "2q_n_v_neg_n_neg_noun_pl": "{} {} nie {} {} nie-{} którzy są {}",
          "2q_n_v_neg_n_neg_noun_neg_si": "{} {} nie {} {} nie-{} który nie jest {}",
          "2q_n_v_neg_n_neg_noun_neg_pl": "{} {} nie {} {} nie-{} którzy nie są {}",
          "2q_n_neg_v_n_noun_si": "{} nie-{} {} {} {} który jest {}",
          "2q_n_neg_v_n_noun_pl": "{} nie-{} {} {} {} którzy są {}",
          "2q_n_neg_v_n_noun_neg_si": "{} nie-{} {} {} {} który nie jest {}",
          "2q_n_neg_v_n_noun_neg_pl": "{} nie-{} {} {} {} którzy nie są {}",
          "2q_n_neg_v_n_neg_noun_si": "{} nie-{} {} {} nie-{} który jest {}",
          "2q_n_neg_v_n_neg_noun_pl": "{} nie-{} {} {} nie-{} którzy są {}",
          "2q_n_neg_v_n_neg_noun_neg_si": "{} nie-{} {} {} nie-{} który nie jest {}",
          "2q_n_neg_v_n_neg_noun_neg_pl": "{} nie-{} {} {} nie-{} którzy nie są {}",
          "2q_n_neg_v_neg_n_noun_si": "{} nie-{} nie {} {} {} który jest {}",
          "2q_n_neg_v_neg_n_noun_pl": "{} nie-{} nie {} {} {} którzy są {}",
          "2q_n_neg_v_neg_n_noun_neg_si": "{} nie-{} nie {} {} {} który nie jest {}",
          "2q_n_neg_v_neg_n_noun_neg_pl": "{} nie-{} nie {} {} {} którzy nie są {}",
          "2q_n_neg_v_neg_n_neg_noun_si": "{} nie-{} nie {} {} nie-{} który jest {}",
          "2q_n_neg_v_neg_n_neg_noun_pl": "{} nie-{} nie {} {} nie-{} którzy są {}",
          "2q_n_neg_v_neg_n_neg_noun_neg_si": "{} nie-{} nie {} {} nie-{} który nie jest {}",
          "2q_n_neg_v_neg_n_neg_noun_neg_pl": "{} nie-{} nie {} {} nie-{} którzy nie są {}",
      }
      return templates[template_name]

  def quantifier_det(self, quantifier):
    det = None
    if quantifier == "all":
      det = random.choice(["każdy", "każdy"])
    elif quantifier == "exists":
      det = random.choice(["pewien", "jakiś"])
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
          template_id += "neg_" 
          if quantifiers[1] == "all":
            dets[1] = "żaden"
        
        template_id += "n_" 
        if negations[variables[1]] == True:
          template_id += "neg_"
        
        template_id += "noun_"
        if negations[variables[2]] == True:
          template_id += "neg_" 
          if quantifiers[0] == "all" and dets[1] != "żaden":
            dets[0] = "żaden"

        template_id += "si"
        
        # ODMIANA DLA SUBJECT
        subj = self.lexicon[variables[0]]["M"]
        verb = self.lexicon[variables[3]]["si"]
        if negations[variables[3]]:
          obj = self.lexicon[variables[1]]["D"]
        else:
          obj = self.lexicon[variables[1]]["B"]
        final_noun = self.lexicon[variables[2]]["N"]
        
        # ODMIANA KWANTYFIKATORA OBIEKTU (det_obj)
        det_obj = dets[1]
        if det_obj == "każdy":
            det_obj = "każdego"
        elif det_obj == "żaden":
            det_obj = "żadnego"
        elif det_obj == "pewien":
            det_obj = "pewnego"
        elif det_obj == "jakiś":
            det_obj = "jakiegoś"
            
        if dets[0] == "żaden" and negations[variables[3]]:
            det_obj = "żadnego"
        
        return self.template_natural_language(template_id,sub_obj_type).format(dets[0], subj, verb, det_obj, obj, final_noun)
          
      elif sub_obj_type == "object":
        template_id = "2q_n_"
        dets = [self.quantifier_det(quantifiers[0]), self.quantifier_det(quantifiers[1])]
        if negations[variables[0]] == True:
          template_id += "neg_"

        template_id += "v_"
        if negations[variables[3]] == True:
          template_id += "neg_" 
          if quantifiers[0] == "all":
            dets[0] = "żaden"
            if quantifiers[1] == "exists":
              dets[1] = "każdy"
            else :
              dets[1] = "żaden"
        
        template_id += "n_" 
        if negations[variables[1]] == True:
          template_id += "neg_"
        
        template_id += "noun_"
        if negations[variables[2]] == True:
          template_id += "neg_"

        template_id += "si"
        
        # ODMIANA DLA OBJECT
        subj = self.lexicon[variables[0]]["M"]
        verb = self.lexicon[variables[3]]["si"]
        if negations[variables[3]]:
          obj = self.lexicon[variables[1]]["D"]
        else:
          obj = self.lexicon[variables[1]]["B"]
        final_noun = self.lexicon[variables[2]]["N"]
        
        # ODMIANA KWANTYFIKATORA OBIEKTU (det_obj)
        det_obj = dets[1]
        if det_obj == "każdy":
            det_obj = "każdego"
        elif det_obj == "żaden":
            det_obj = "żadnego"
        elif det_obj == "pewien":
            det_obj = "pewnego"
        elif det_obj == "jakiś":
            det_obj = "jakiegoś"
            
        if dets[0] == "żaden" and negations[variables[3]]:
            det_obj = "żadnego"
        
        return self.template_natural_language(template_id, sub_obj_type).format(dets[0], subj, verb, det_obj, obj, final_noun)

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
  def __init__(self, functions, lexicon):
    self.quantifiers = ["all", "exists"]
    self.functions = functions
    self.lexicon = lexicon

  def template_natural_language(self, template_name):
    templates = {
        "2q_n_v_n_v_si_si": "{} {} {} {} {} który {} {}",
        "2q_n_v_n_v_neg_si_si": "{} {} {} {} {} który nie {} {}",
        "2q_n_v_neg_n_v_si_si": "{} {} nie {} {} {} który {} {}",
        "2q_n_v_neg_n_v_neg_si_si": "{} {} nie {} {} {} który nie {} {}",
        "2q_n_v_n_neg_v_si_si": "{} {} {} {} nie-{} który {} {}",
        "2q_n_v_n_neg_v_neg_si_si": "{} {} {} {} nie-{} który nie {} {}",
        "2q_n_v_neg_n_neg_v_si_si": "{} {} nie {} {} nie-{} który {} {}",
        "2q_n_v_neg_n_neg_v_neg_si_si": "{} {} nie {} {} nie-{} który nie {} {}",
        "2q_n_neg_v_n_v_si_si": "{} nie-{} {} {} {} który {} {}",
        "2q_n_neg_v_n_v_neg_si_si": "{} nie-{} {} {} {} który nie {} {}",
        "2q_n_neg_v_neg_n_v_si_si": "{} nie-{} nie {} {} {} który {} {}",
        "2q_n_neg_v_neg_n_v_neg_si_si": "{} nie-{} nie {} {} {} który nie {} {}",
        "2q_n_neg_v_n_neg_v_si_si": "{} nie-{} {} {} nie-{} który {} {}",
        "2q_n_neg_v_n_neg_v_neg_si_si": "{} nie-{} {} {} nie-{} który nie {} {}",
        "2q_n_neg_v_neg_n_neg_v_si_si": "{} nie-{} nie {} {} nie-{} który {} {}",
        "2q_n_neg_v_neg_n_neg_v_neg_si_si": "{} nie-{} nie {} {} nie-{} który nie {} {}"
      }
    return templates[template_name]

  def quantifier_det(self, quantifier):
    det = None
    if quantifier == "all":
      det = random.choice(["każdy", "każdy"])
    elif quantifier == "exists":
      det = random.choice(["pewien", "jakiś"])
    return det


  def natural_language_sentence_generation(self, quantifiers, variables, negations):
    dets = [self.quantifier_det(quantifiers[0]), self.quantifier_det(quantifiers[1])]
    template_id = "2q_n_"

    if negations[variables[0]] == True:
      template_id += "neg_"
    template_id += "v_"
    if negations[variables[3]] == True:
      template_id += "neg_" 
      if quantifiers[0] == "all":
        dets[0] = "żaden"
        if quantifiers[1] == "all":
          dets[1] = "żaden"
        else :
          dets[1] = "każdy"
      elif (quantifiers[0] == "exists") and (quantifiers[1] == "exists"):
        dets[1] = "żaden"
      
    template_id += "n_"
    if negations[variables[1]] == True:
      template_id += "neg_"
    template_id += "v_"
    if negations[variables[2]] == True:
      template_id += "neg_"
    
    template_id += "si_"
    pronoun = "go"
    template_id += "si"

    # ODMIANA DLA ANAPHORY
    subj = self.lexicon[variables[0]]["M"]
    verb1 = self.lexicon[variables[3]]["si"]
    verb2 = self.lexicon[variables[2]]["si"]
    
    if negations[variables[3]]:
      obj = self.lexicon[variables[1]]["D"]
    else:
      obj = self.lexicon[variables[1]]["B"]
      
    det_obj = dets[1]
    if det_obj == "każdy":
        det_obj = "każdego"
    elif det_obj == "żaden":
        det_obj = "żadnego"
    elif det_obj in ["pewien", "jakiś"]:
        det_obj = random.choice(["pewnego", "jakiegoś"])
        
    if dets[0] == "żaden" and negations[variables[3]]:
        det_obj = "żadnego"

    return self.template_natural_language(template_id).format(dets[0], subj, verb1, det_obj, obj, verb2, pronoun)

    
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