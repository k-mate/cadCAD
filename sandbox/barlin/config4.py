from decimal import Decimal
import numpy as np
from datetime import timedelta

from SimCAD import Configuration, configs
from SimCAD.configuration.utils import exo_update_per_ts, proc_trigger, bound_norm_random, \
    ep_time_step

seed = {
    'z': np.random.RandomState(1)
}

# Signals
# Pr_signal
beta = Decimal('0.25') # agent response gain
beta_LT = Decimal('0.1') # LT agent response gain
# alpha = .67, 2 block moving average
alpha = Decimal('0.67') # 21 day EMA forgetfullness between 0 and 1, closer to 1 discounts older obs quicker, should be 2/(N+1)
max_withdraw_factor = Decimal('0.9')
external_draw = Decimal('0.01') # between 0 and 1 to draw Buy_Log to external


#alpha * s['Zeus_ST'] + (1 - alpha)*s['Zeus_LT']

# Stochastic process factors
correction_factor = Decimal('0.01')
volatility =  Decimal('5.0')

# Buy_Log_signal =
# Z_signal =
# Price_signal =
# TDR_draw_signal =
# P_Ext_Markets_signal =

# Behaviors per Mechanism

# BEHAVIOR 1: EMH Trader
EMH_portion = Decimal('0.250')
EMH_Ext_Hold = Decimal('42000.0')


def b1m1(step, sL, s):
#    print('b1m1')
    theta = (s['Z']*EMH_portion*s['Price'])/(s['Z']*EMH_portion*s['Price'] + EMH_Ext_Hold * s['P_Ext_Markets'])
    if s['Price'] < (theta*EMH_Ext_Hold * s['P_Ext_Markets'])/(s['Z']*EMH_portion*(1-theta)):
        buy = beta * theta*EMH_Ext_Hold * s['P_Ext_Markets']/(s['Price']*EMH_portion*(1-theta))
        return {'buy_order1': buy}
    elif s['Price'] > (theta*EMH_Ext_Hold * s['P_Ext_Markets'])/(s['Z']*EMH_portion*(1-theta)):
        return {'buy_order1': 0}
    else:
        return {'buy_order1': 0}


def b1m2(step, sL, s):
#    print('b1m2')
    theta = (s['Z']*EMH_portion*s['Price'])/(s['Z']*EMH_portion*s['Price'] + EMH_Ext_Hold * s['P_Ext_Markets'])
    if s['Price'] < (theta*EMH_Ext_Hold * s['P_Ext_Markets'])/(s['Z']*EMH_portion*(1-theta)):
        return {'sell_order1': 0}
    elif s['Price'] > (theta*EMH_Ext_Hold * s['P_Ext_Markets'])/(s['Z']*EMH_portion*(1-theta)):
        sell = beta * theta*EMH_Ext_Hold * s['P_Ext_Markets']/(s['Price']*EMH_portion*(1-theta))
        return {'sell_order1': sell}
    else:
        return {'sell_order1': 0}

# BEHAVIOR 3: Herding
Herd_portion = Decimal('0.250')
Herd_Ext_Hold = Decimal('42000.0')
Herd_UB = Decimal('0.10') # UPPER BOUND
Herd_LB = Decimal('0.10') # LOWER BOUND
def b3m2(step, sL, s):
    theta = (s['Z']*Herd_portion*s['Price'])/(s['Z']*Herd_portion*s['Price'] + Herd_Ext_Hold * s['P_Ext_Markets'])
#    if s['Price'] - s['Price_Signal'] <  (theta*Herd_Ext_Hold * s['P_Ext_Markets'])/(s['Z']*Herd_portion*(1-theta)) - Herd_LB:
    if (s['Price'] - s['Price_Signal']) < - Herd_LB:

        sell = beta * theta*Herd_Ext_Hold * s['P_Ext_Markets']/(s['Price']*Herd_portion*(1-theta))
        return {'herd_sell': sell, 'herd_buy': 0}
      #  elif s['Price'] > Herd_UB - (theta*Herd_Ext_Hold * s['P_Ext_Markets'])/(s['Z']*Herd_portion*(1-theta)):
    elif (s['Price'] - s['Price_Signal']) > Herd_UB:
        buy = beta * theta*Herd_Ext_Hold * s['P_Ext_Markets']/(s['Price']*Herd_portion*(1-theta))
        return {'herd_sell': 0, 'herd_buy': buy}
    else:
        return {'herd_sell': 0, 'herd_buy': 0}

# BEHAVIOR 4: HODLers
HODL_belief = Decimal('10.0')
HODL_portion = Decimal('0.250')
HODL_Ext_Hold = Decimal('4200.0')


def b4m2(step, sL, s):
#    print('b4m2')
    theta = (s['Z']*HODL_portion*s['Price'])/(s['Z']*HODL_portion*s['Price'] + HODL_Ext_Hold * s['P_Ext_Markets'])
    if s['Price'] <  1/HODL_belief*(theta*HODL_Ext_Hold * s['P_Ext_Markets'])/(s['Z']*HODL_portion*(1-theta)):
        sell = beta * theta*HODL_Ext_Hold * s['P_Ext_Markets']/(s['Price']*HODL_portion*(1-theta))
        return {'sell_order2': sell}
    elif s['Price'] > (theta*HODL_Ext_Hold * s['P_Ext_Markets'])/(s['Z']*HODL_portion*(1-theta)):
        return {'sell_order2': 0}
    else:
        return {'sell_order2': 0}


# STATES
# ZEUS Fixed Supply
def s1m1(step, sL, s, _input):
    y = 'Z'
    x = s['Z'] #+  _input # / Psignal_int
    return (y, x)


# def s2m1(step, sL, s, _input):
#     y = 'Price'
#     x = (s['P_Ext_Markets'] - _input['buy_order1']) / s['Z'] * 10000
#     #x= alpha * s['Z'] + (1 - alpha)*s['Price']
#     return (y, x)


def s3m1(step, sL, s, _input):
    y = 'Buy_Log'
    x = _input['buy_order1'] + _input['herd_buy'] # / Psignal_int
    return (y, x)


def s4m2(step, sL, s, _input):
    y = 'Sell_Log'
    x = _input['sell_order1'] + _input['sell_order2'] + _input['herd_sell'] # / Psignal_int
    return (y, x)


def s3m3(step, sL, s, _input):
    y = 'Buy_Log'
    x = s['Buy_Log'] +  _input # / Psignal_int
    return (y, x)


# Price Update
def s2m3(step, sL, s, _input):

    y = 'Price'
    #var1 = Decimal.from_float(s['Buy_Log'])
    x = s['Price'] + s['Buy_Log'] /s['Z'] - s['Sell_Log']/s['Z']
     #+ np.divide(s['Buy_Log'],s['Z']) - np.divide() # / Psignal_int
    return (y, x)

def s5m3(step, sL, s, _input):
    y = 'Price_Signal'
    x = alpha * s['Price'] + (1 - alpha)*s['Price_Signal']
    return (y, x)

def s6m1(step, sL, s, _input):
    y = 'P_Ext_Markets'
    x = s['P_Ext_Markets'] - _input
    #x= alpha * s['Z'] + (1 - alpha)*s['Price']
    return (y, x)


def s2m2(step, sL, s, _input):
    y = 'Price'
    x = (s['P_Ext_Markets'] - _input) /s['Z'] *10000
    #x= alpha * s['Z'] + (1 - alpha)*s['Price']
    return (y, x)

# Exogenous States
proc_one_coef_A = -125
proc_one_coef_B = 125

# A change in belief of actual price, passed onto behaviors to make action
def es4p2(step, sL, s, _input):
    y = 'P_Ext_Markets'
    x = s['P_Ext_Markets'] +  bound_norm_random(seed['z'], proc_one_coef_A, proc_one_coef_B)

    return (y,x)


ts_format = '%Y-%m-%d %H:%M:%S'
t_delta = timedelta(days=0, minutes=0, seconds=1)
def es5p2(step, sL, s, _input):
    y = 'timestamp'
    x = ep_time_step(s, dt_str=s['timestamp'], fromat_str=ts_format, _timedelta=t_delta)
    return (y, x)

#Environment States
# NONE

# Genesis States
state_dict = {
    'Z': Decimal(21000000.0),
    'Price': Decimal(100.0),  # Initialize = Z for EMA
    'Buy_Log': Decimal(0.0),
    'Sell_Log': Decimal(0.0),
    'Price_Signal': Decimal(100.0),
    'Trans': Decimal(0.0),
    'P_Ext_Markets': Decimal(25000.0),
    'timestamp': '2018-10-01 15:16:24'
}

def env_proc_id(x):
    return x

env_processes = {}

exogenous_states = exo_update_per_ts(
    {
    "P_Ext_Markets": es4p2,
    "timestamp": es5p2
    }
)

sim_config = {
    "N": 20,
    "T": range(1000)
}

# test return vs. non-return functions as lambdas
# test fully defined functions
mechanisms = {
    "m1": {
        "behaviors": {
            "b1": b1m1,
            "b3": b3m2
        },
        "states": {
            "Z": s1m1,
            "Buy_Log": s3m1
        }
    },
    "m2": {
         "behaviors": {
            "b1": b1m2,
            "b3": b3m2,
            "b4": b4m2
         },
         "states": {
             "Sell_Log": s4m2
        }
    },
    "m3": {
            "behaviors": {
        },
            "states": {
                "Price": s2m3,
                "Price_Signal": s5m3
        }
    }
}

configs.append(Configuration(sim_config, state_dict, seed, exogenous_states, env_processes, mechanisms))