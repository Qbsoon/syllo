from z3 import *
import numpy as np
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

from typing import List, Dict, Any, Union, Optional
import io


import random
import re
import time

import numpy as np
import pandas as pd

from nltk.parse.generate import generate
from fragments import (
  SyllogisticTemplates,
  RelationalSyllogiticTemplates, 
  RelativeClausesTemplates, 
  RelativeTVTemplates, 
  AnaphoraTemplates,
)


from tqdm import tqdm


nouns = [
    "actor","artist","butler","crook","director",
    "expert","fisherman","judge","juror","painter","musician",
    "policeman","fireman","professor","sheriff","soldier","student",
    "philosopher","teacher","tourist","lawyer","physician","engineer",
    "veterinarian","dentist","accountant","technician","electrician",
    "psychologist","physicist","plumber","waiter","mechanic","cook",
    "librarian","hairdresser","economist","bartender","cashier","surgeon",
    "pilot","butcher","optician","athlete","cleaner",
    "actuary","sailor","therapist","secret_agent","animal_breeder","air_traffic_controller",
    "athropologist","animal_trainer","allergist","real_estate_agent","archeologist",
    "astronomer","athletic_trainer","audiologist","auditor","bailiff",
    "baker","barber","clerk","cartographer","chiropractor","dancer","epidemiologist",
    "farmer","floral_designer","forester","truck_driver","jeweler","interior_designer",
    "machinist","mathematician","secretary","photographer","radio_announcer","roofer",
    "paver","taxi_driver","historian","poet","stunt_performer","monologist","publisher",
    "scribe","blogger","copy_editor","ceo","ticket_controller","station_master","surveyor",
    "driller", "scholar", "quant", "cfo" , "cto", "cio", "computer_scientist", "prisoner", 
    "guest", "visitor", "helper", "breadwinner", "host", "ghost", "playmaker", "scorer", 
    "settler", "reacher", "cynic", "witch", "captain", "buisness_analyst", "data_scientist",
    "trader", "principal", "ballerina", "footballer", "cricketer", "tennis_player", "lecturer", 
    "patient", "ai_scientist", "philosopher", "cyclist", "chess_player", "stratergist", 
    "scientist", "parent", "fbi_agent", "defender" , "attacker", "warlord", "nlp_engineer", 
    "grandmaster", "master", "king", "queen", "knight", "prince", "princess", "baby", "adult",
    "advisor", "wrestler", "fighter", "boxer", "bee_keeper", "musian", "dj_artist", "violinist",
    "conductor", "gymnast"
]

count_furniture = [
    "chair","table","desk","stool","couch","bookcase",
    "bed","mattress","dresser","futon","nightstand","storage_container",
    "hammock","billiard_table","piano","chess_board","door",
]


count_animals = [
    "aardvark","dog","alpaca","armadillo","anteater","penguin",
    "ant","bear","bonobo","beaver","bird","owl","butterfly",
    "buffalo","bumblebee","frog","whale","bison","badger","baboon",
    "rhinoceros","camel","cat","chicken","cheetah","cockatoo","cow","crab",
    "catepillar","chimpanzee","loon","spider","crocodile","coyote","chincilla",
    "duck","deer","dolphin","dingo","donkey","eel","elephant","emu","gorilla","falcon",
    "fox","ferret","gerbil","grasshopper","gopher","goat","hyena","horse","hippopotamus",
    "jaguar","kangaroo","lemur","lion","lynx","lizard","marmot","mink","muskrat","mouse",
    "macaw","moose","newt","ostrich","otter","pig","puffin","puma","pelican","peacock",
    "rabbit","snake","reindeer","raccoon","rat","sheep","vulture","wombat","wolf","warthog",
    "walrus","weasel","boar","zebra","seal",
]

verbs = ["like", "admire", "make", "break", "employ",
         "hit", "kill", "fight", "touch", "slay",
         "approve", "defend", "replace", "chase", "hunt",
         "dislike", "recognize", "understand", "feel",
         "love", "hate", "impress", "know", "notice", "perceive", 
         "see", "remember", "surprise", "prefer",
         "draw", "accuse", "adore", "advise", "appreciate", 
         "approach", "astonish", "need", "call", "believe",
         "follow", "serve", "consult", "convince", "criticize", 
         "desire", "doubt", "encourage", "examine",
         "feed", "forgive", "hug", "investigate", "kiss", 
         "mention", "owe", "persuade", "propose", "promise",
         "punch", "shoot", "threaten", "tolerate", "warn", 
         "esteem", "marvel", "fancy", "utilize", "slaughter",
         "endorse", "support"]


def parse_args():
    parser = argparse.ArgumentParser(description="data construction SAT")

    parser.add_argument(
        "--fragment",
        type=str,
        default=None,
        required = True,
        help="The name of the language fragment to generate the data",
    )

    parser.add_argument(
        "--sampling_file",
        type=str,
        default=None,
        required = True,
        help="File contianing the disribution of satisfiablity of the language fragment",
    )

    parser.add_argument(
        "--min_ab",
        type=float,
        default=0.35,
        help="minimum prob value of the phase change region",
    )

    parser.add_argument(
        "--max_ab",
        type=float,
        default=0.65,
        help="maximum prob value of the phase change region",
    )

    parser.add_argument(
        "--max_a",
        type=int,
        default=5,
        help="maximum number of unary predicates",
    )

    parser.add_argument(
        "--max_b",
        type=int,
        default=5,
        help="maximum number of binary predicates",
    )

    parser.add_argument(
        "--min_a",
        type=int,
        default=3,
        help="minimum number of unary predicates",
    )

    parser.add_argument(
        "--min_b",
        type=int,
        default=2,
        help="minimum number of binary predicates",
    )

    parser.add_argument(
        "--time_out",
        type=int,
        default=10000,
        help="Timeout value for the Z3 theorem prover",
    )

    parser.add_argument(
        "--prob",
        type=float,
        default=0.5,
        help="probability of sentences belong to the more complex sub fragments whithin a datapoint",
    )

    parser.add_argument(
        "--num_datapoints",
        type=int,
        default=50000,
        help="number of datapoints",
    )

    parser.add_argument(
        "--output_file",
        type=str,
        default='fragment.csv',
    )

    args = parser.parse_args()

    return args


class LangaugeFragmentSAT:


  def __init__(self, functions, language_fragment, df_hard, min_a = 3, max_a = 8, min_b = 3, max_b = 8, timeout = 10000, prob = 0.5, a_b = 2):

    self.syl_templates = SyllogisticTemplates(functions)
    self.relsyl_templates = RelationalSyllogiticTemplates(functions)
    self.relative_templates = RelativeClausesTemplates(functions)
    self.relative_tv_templates = RelativeTVTemplates(functions)
    self.anaphora_templates = AnaphoraTemplates(functions)
    self.langauge_fragment = language_fragment
    self.timeout = timeout
    self.df_hard = df_hard
    self.min_m_a = df_hard['m/a'].min()
    self.max_m_a = df_hard['m/a'].max()
    self.m_a = df_hard['m/a'].to_list()
    self.min_a = min_a
    self.max_a = max_a
    self.min_b = min_b
    self.max_b = max_b
    self.prob = prob
    self.dist = beta(a_b, a_b)

  def generate_syllogistic(self, nouns, verbs, x, y, unary = 3, binary = 3, num_clauses = 6):
    s = Solver()

    list_fol = []
    list_sentences = []
    list_quantifiers = []


    unary_preds = random.sample(nouns, unary)
    binary_preds = random.sample(verbs, binary)
    prob = 1

    for i in range(num_clauses):
      logic, sentence, quantifiers  = self.syl_templates.generate_sentence_logic_pair(unary_preds, binary_preds, x, y, negations = True)
    
      list_fol.append(logic)
      list_sentences.append(sentence)
      list_quantifiers.append(quantifiers)

    s.add(list_fol)
    s.set("timeout", self.timeout)
    sat = str(s.check())

    return list_fol, list_sentences, list_quantifiers, sat, prob

  

  def generate_relative_clauses(self, nouns, verbs, x, y, unary = 3, binary = 3, num_clauses = 6):

    s = Solver()

    list_fol = []
    list_sentences = []
    list_quantifiers = []

    unary_preds = random.sample(nouns, unary)
    binary_preds = random.sample(verbs, binary)

    prob = self.prob

    for i in range(num_clauses):
      if random.uniform(0,1) < prob :
        logic, sentence, quantifiers  = self.relative_templates.generate_sentence_logic_pair(unary_preds, binary_preds, x, y)
      else :
        logic, sentence, quantifiers  = self.syl_templates.generate_sentence_logic_pair(unary_preds, binary_preds, x, y)

      list_fol.append(logic)
      list_sentences.append(sentence)
      list_quantifiers.append(quantifiers)

    s.add(list_fol)

    s.set("timeout", self.timeout)
    sat = str(s.check())

    return list_fol, list_sentences, list_quantifiers, sat, prob

  
  def generate_relational_syllogistic(self, nouns, verbs, x, y, unary = 3, binary = 3, num_clauses = 6):

    s = Solver()

    list_fol = []
    list_sentences = []
    list_quantifiers = []

    unary_preds = random.sample(nouns, unary)
    binary_preds = random.sample(verbs, binary)

    prob = self.prob

    for i in range(num_clauses):
      if random.uniform(0,1) < prob :
        logic, sentence, quantifiers  = self.relsyl_templates.generate_sentence_logic_pair(unary_preds, binary_preds, x, y)
      else :
        random_fragment = random.choice(["syl", "rel"])
        if random_fragment == "syl":
          logic, sentence, quantifiers  = self.syl_templates.generate_sentence_logic_pair(unary_preds, binary_preds, x, y)
        else :
          logic, sentence, quantifiers  = self.relative_templates.generate_sentence_logic_pair(unary_preds, binary_preds, x, y)
        
      list_fol.append(logic)
      list_sentences.append(sentence)
      list_quantifiers.append(quantifiers)

    s.add(list_fol)

    s.set("timeout", self.timeout)
    sat = str(s.check())

    return list_fol, list_sentences, list_quantifiers, sat, prob

  
  def generate_relative_tv(self, nouns, verbs, x, y, unary = 3, binary = 3, num_clauses = 6):

    s = Solver()

    list_fol = []
    list_sentences = []
    list_quantifiers = []


    unary_preds = random.sample(nouns, unary)
    binary_preds = random.sample(verbs, binary)

    prob = self.prob
    for i in range(num_clauses):
      if random.uniform(0,1) < prob :
        logic, sentence, quantifiers  = self.relative_tv_templates.generate_sentence_logic_pair(unary_preds, binary_preds, x, y)
      else :
        random_fragment = random.choice(["syl", "re-syl", "rel"])
        if random_fragment == "syl":
          logic, sentence, quantifiers  = self.syl_templates.generate_sentence_logic_pair(unary_preds, binary_preds, x, y)
        elif random_fragment == "re-syl" :
          logic, sentence, quantifiers  = self.relsyl_templates.generate_sentence_logic_pair(unary_preds, binary_preds, x, y)
        else :
          logic, sentence, quantifiers  = self.relative_templates.generate_sentence_logic_pair(unary_preds, binary_preds, x, y)
      list_fol.append(logic)
      list_sentences.append(sentence)
      list_quantifiers.append(quantifiers)

    s.add(list_fol)
    s.set("timeout", self.timeout)
    sat = str(s.check())

    return list_fol, list_sentences, list_quantifiers, sat, prob

  def generate_anaphora(self, nouns, verbs, x, y, unary = 3, binary = 3, num_clauses = 6):

    s = Solver()

    list_fol = []
    list_sentences = []
    list_quantifiers = []


    unary_preds = random.sample(nouns, unary)
    binary_preds = random.sample(verbs, binary)

    prob = self.prob
    for i in range(num_clauses):
      if random.uniform(0,1) < prob :
        logic, sentence, quantifiers  = self.anaphora_templates.generate_sentence_logic_pair(unary_preds, binary_preds, x, y)
      else :
        random_fragment = random.choice(["syl", "re-syl", "rel","syl", "re-syl", "rel", "rel_tv"])
        if random_fragment == "syl":
          logic, sentence, quantifiers  = self.syl_templates.generate_sentence_logic_pair(unary_preds, binary_preds, x, y)
        elif random_fragment == "re-syl" :
          logic, sentence, quantifiers  = self.relsyl_templates.generate_sentence_logic_pair(unary_preds, binary_preds, x, y)
        elif random_fragment == "rel" :
          logic, sentence, quantifiers  = self.relative_templates.generate_sentence_logic_pair(unary_preds, binary_preds, x, y)
        else :
          logic, sentence, quantifiers  = self.relative_tv_templates.generate_sentence_logic_pair(unary_preds, binary_preds, x, y)
      list_fol.append(logic)
      list_sentences.append(sentence)
      list_quantifiers.append(quantifiers)

    s.add(list_fol)
    s.set("timeout", self.timeout)
    sat = str(s.check())

    return list_fol, list_sentences, list_quantifiers, sat, prob

  def generate_datapoint(self, nouns, verbs, x, y, unary = 3, binary = 3, num_clauses = 6):
    if self.langauge_fragment == "syllogistic":
      time.sleep(0.01)
      return self.generate_syllogistic(nouns, verbs, x, y, unary, binary, num_clauses)
    elif self.langauge_fragment == "syllogistic minus":
      time.sleep(0.01)
      return self.generate_syllogistic_minus(nouns, verbs, x, y, unary, binary, num_clauses)
    elif self.langauge_fragment == "relational syllogistic":
      return self.generate_relational_syllogistic(nouns, verbs, x, y, unary, binary, num_clauses)
    elif self.langauge_fragment == "relative clauses":
      return self.generate_relative_clauses(nouns, verbs, x, y, unary, binary, num_clauses)
    elif self.langauge_fragment == "relative transitive verbs":
      time.sleep(0.01)
      return self.generate_relative_tv(nouns, verbs, x, y, unary, binary, num_clauses)
    elif self.langauge_fragment == "anaphora":
      time.sleep(0.01)
      return self.generate_anaphora(nouns, verbs, x, y, unary, binary, num_clauses)


  def generator(self):
    while True:
      yield

 
  def create_df(self, nouns, verbs, x, y, num_datapoints=10000):

    data = {
        "formulae" : [],
        "sentences" : [],
        "quantifiers" : [],
        "sat" : [],
        "unary" : [],
        "binary" : [],
        "num_clauses" : [],
        "prob" : []
    }
    
    count = 0
    iter = 0

    progress_bar = tqdm(range(num_datapoints))

    while (True):

      
      if (self.langauge_fragment == "syllogistic") or (self.langauge_fragment == "relative clauses") or ((self.langauge_fragment == "syllogistic minus")):

        sample = self.min_a + self.dist.rvs(size=1) * (self.max_a - self.min_a)

        unary = round(sample[0])
        num_clauses = round(random.uniform(self.min_m_a, self.max_m_a) * unary)
        binary = 1
      else :
        unary = random.randint(self.min_a, self.max_a)
        num_clauses = round(random.uniform(self.min_m_a, self.max_m_a) * unary)
        m_a_ratio = min(self.m_a, key=lambda x:abs(x - num_clauses/unary))

        min_m_b = self.df_hard[self.df_hard['m/a'] == m_a_ratio]['m/b'].min()
        max_m_b = self.df_hard[self.df_hard['m/a'] == m_a_ratio]['m/b'].max()
        
        binary = round(num_clauses / random.uniform(min_m_b, max_m_b))
        if (binary > self.max_b) or (binary < self.min_b) :
          continue 
      list_fol, list_sentences, list_quantifiers, sat, prob = self.generate_datapoint(nouns, verbs, x, y, unary, binary, num_clauses)

      iter += 1

      if sat != "unknown":
        data["formulae"].append(list_fol)
        data["sentences"].append(list_sentences)
        data["quantifiers"].append(list_quantifiers)
        data["sat"].append(sat)
        data["unary"].append(unary)
        data["binary"].append(binary)
        data["num_clauses"].append(num_clauses)
        data["prob"].append(prob)

        count += 1

        progress_bar.update(1)
                  
      
      if count >= num_datapoints :
        break

      if iter % 1000 == 0 :
        print(iter, count)


    df = pd.DataFrame(data)
    return df

# TODO: Martin
def run_engine(
    num_datapoints: int,
    sampling_data: Union[str, List[Dict[str, Any]]],
    fragment: str,
    min_a: int,
    max_a: int,
    min_ab: float = 0.35,
    max_ab: float = 0.65,
    timeout: int = 10000
) -> pd.DataFrame:
    """Wrapper for the NLSAT engine to be called by the Quart server.

    Args:
        num_datapoints: Number of syllogisms to generate.
        sampling_data: Sampling distribution as a JSON string or list of dicts.
        fragment: Name of the language fragment (e.g., 'syllogistic').
        min_a: Minimum number of unary predicates.
        max_a: Maximum number of unary predicates.
        min_ab: Minimum probability for phase change region.
        max_ab: Maximum probability for phase change region.
        timeout: Z3 solver timeout in milliseconds.

    Returns:
        pd.DataFrame: The generated dataset.
    """
    set_param(proof=True)
    x, y = Ints('x y')
    Z, B = IntSort(), BoolSort()

    functions = {f: Function(f, Z, B) for f in nouns}
    functions.update({f: Function(f, Z, Z, B) for f in verbs})

    if isinstance(sampling_data, str):
        df_agg = pd.read_json(io.StringIO(sampling_data))
    else:
        df_agg = pd.DataFrame(sampling_data)

    df_hard = df_agg[(df_agg['is_sat'] < max_ab) & (df_agg['is_sat'] > min_ab)]

    sat_fragment = LangaugeFragmentSAT(
        functions, fragment, df_hard, 
        min_a=min_a, max_a=max_a, timeout=timeout
    )
    
    df = sat_fragment.create_df(nouns, verbs, x, y, num_datapoints=num_datapoints)
    return df