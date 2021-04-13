#!/usr/bin/env python3

"""Script to combine and filter ShopKeep CSV reports."""

# Copyright 2021 Scott A. Anderson
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import argparse
import configparser
import csv
import fileinput
from pathlib import Path
import sys

PROG_DESCRIPTION = 'Combine ShopKeep CSV reports'

COMMON_FIELDS = {
    'Transaction ID',
    'Time',
    'Register Name/Number',
    'Cashier Name',
    'Operation Type',
    'Net Total',		# Value differs between ITEM and TENDER
    'Tax',			# Value differs between ITEM and TENDER
    'Total Due'			# Value differs between ITEM and TENDER
    }
ITEM_FIELDS = COMMON_FIELDS | {
    'Category',
    'Cost',
    'Customer ID',
    'Department',
    'Discounts',
    'Line Item',
    'Modifiers',
    'Price',
    'Quantity',
    'Store Code',
    'Subtotal',
    'Supplier Code',
    'Supplier',
    'UPC'
}
TENDERS_FIELDS = COMMON_FIELDS | {
    'Card Type',
    'Cardholder Name',
    'Customer Email',
    'Customer Name',
    'Discount',
    'Gross Amount',
    'Last 4 Digits',
    'New Liabilities',
    'Receipt Number',
    'Tender Type',
    'Tendered Amount',
    'Tips'
}

def list_from_comma_separated_string(csstr):
    str_l = csstr.split(',')
    valid_fields = ITEM_FIELDS | TENDERS_FIELDS
    if not set(str_l).issubset(valid_fields):
        raise ValueError
    return str_l

def set_from_comma_separated_string(csstr):
    str_s = set(csstr.split(','))
    if str_s - ITEM_FIELDS - TENDERS_FIELDS:
        raise ValueError
    return str_s

def get_args():
    argp = argparse.ArgumentParser(
        description=PROG_DESCRIPTION,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    argp.add_argument('-F', '--config-file',
                      default=Path('~/.shopkeep_combine_csv.rc').expanduser(),
                      help='The configuration file to use.')
    argp.add_argument('-c', '--config-section', default='DEFAULT',
                      help='The section of the configuration file to use.')
    iore = argp.add_mutually_exclusive_group()
    iore.add_argument('-i', '--include', type=list_from_comma_separated_string,
                      help='Only output specified columns in order specified.')
    iore.add_argument('-x', '--exclude', type=set_from_comma_separated_string,
                      help='Output all columns except the specified columns')
    argp.add_argument('tenders_CSV', type=fileinput.input,
                      help='ShopKeep "Transactions Tenders" report')
    argp.add_argument('item_CSV', type=fileinput.input, help=
                      'Corresponding ShopKeep "Transactions by Item" report')
    argp.add_argument('output', type=argparse.FileType('w'), default='-',
                      nargs='?', help='The output file')
    args = argp.parse_args()

    cfgp = configparser.ConfigParser()
    cfgp.read(args.config_file)
    cfg = cfgp[args.config_section]

    if args.include is None and args.exclude is None:
        cfg_val = cfg.get('include', None)
        if cfg_val:
            args.include = list_from_comma_separated_string(cfg_val)
        cfg_val = cfg.get('exclude', None)
        if cfg_val:
            args.exclude = set_from_comma_separated_string(cfg_val)
        if args.include is not None and args.exclude is not None:
            print(f'Ignoring exclude from section {args.config_section} '
                  f'of {args.config_file}.', file=sys.stderr)
            args.exclude = None

    return args

def main():
    args = get_args()

    # Process tenders CSV
    csv_reader = csv.DictReader(args.tenders_CSV, restkey='Unexpected Fields')
    tenders_fieldnames = csv_reader.fieldnames
    if set(tenders_fieldnames) != TENDERS_FIELDS:
        print(f'{args.tenders_CSV} is not a "Transactions Tenders" report.',
              file=sys.stderr)
        return 1

    tenders_dup = {}
    tenders = {}
    for row in csv_reader:
        if None in row.values():
            print(f'Empty value in tender from {args.tenders_CSV}.',
                  file=sys.stderr)
            return 1
        if 'Unexpected Fields' in row:
            print(f'Extra value in tender from {args.tenders_CSV}.',
                  file=sys.stderr)
            return 1

        tenders_dup[row['Transaction ID']] = {
            'Time':row['Time'],
            'Register Name/Number':row['Register Name/Number'],
            'Cashier Name':row['Cashier Name'],
            'Operation Type':row['Operation Type']
        }

        tenders[row['Transaction ID']] = {
            'Customer Name':row['Customer Name'],
            'Customer Email':row['Customer Email'],
            'Gross Amount':row['Gross Amount'],
            'Discount':row['Discount'],
            'Tenders Net Total':row['Net Total'],
            'New Liabilities':row['New Liabilities'],
            'Tenders Tax':row['Tax'],
            'Tenders Total Due':row['Total Due'],
            'Tips':row['Tips'],
            'Tendered Amount':row['Tendered Amount'],
            'Tender Type':row['Tender Type'],
            'Card Type':row['Card Type'],
            'Last 4 Digits':row['Last 4 Digits'],
            'Cardholder Name':row['Cardholder Name'],
            'Receipt Number':row['Receipt Number']
        }

    # Process item CSV
    csv_reader = csv.DictReader(args.item_CSV, restkey='Unexpected Fields')
    item_fieldnames = csv_reader.fieldnames
    tenders_fieldnames = list(tenders[list(tenders)[0]])

    if set(item_fieldnames) != ITEM_FIELDS:
        print(f'{args.tenders_CSV} is not a "Transactions by Item" report.',
              file=sys.stderr)
        return 1

    if args.include:
        fields = args.include
    else:
        fields = item_fieldnames + tenders_fieldnames
        if args.exclude:
            fields = [val for val in fields if val not in args.exclude]

    print(','.join(fields), file=args.output)

    for row in csv_reader:
        if None in row.values():
            print(f'Empty value in item from {args.tenders_CSV}.',
                  file=sys.stderr)
            return 1
        if 'Unexpected Fields' in row:
            print(f'Extra value in item from {args.tenders_CSV}.',
                  file=sys.stderr)
            return 1

        t_id = row['Transaction ID']
        if t_id not in tenders:
            print(f'{t_id} is not in {args.tenders_CSV}.', file=sys.stderr)
            return 1

        for key in tenders_dup[t_id]:
            if tenders_dup[t_id][key] != row[key]:
                print(f'Mismatch between item and tender for {key}.',
                      file=sys.stderr)
                return 1

        row.update(tenders[t_id])

        values = [row[key] for key in fields]
        print(','.join(values), file=args.output)

    return 0

if __name__ == '__main__':
    sys.exit(main())
