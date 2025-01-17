"""Norwegian-specific Form helpers."""

from __future__ import unicode_literals

import datetime
import re

from django.core.validators import EMPTY_VALUES
from django.forms import ValidationError
from django.forms.fields import CharField, Field, RegexField, Select
from django.utils.translation import ugettext_lazy as _

from localflavor.compat import EmptyValueCompatMixin
from localflavor.deprecation import DeprecatedPhoneNumberFormFieldMixin

from .no_municipalities import MUNICIPALITY_CHOICES


class NOZipCodeField(RegexField):
    """
    A form field that validates input as a Norwegian zip code.

    Valid codes have four digits.
    """

    default_error_messages = {
        'invalid': _('Enter a zip code in the format XXXX.'),
    }

    def __init__(self, max_length=None, min_length=None, *args, **kwargs):
        super(NOZipCodeField, self).__init__(r'^\d{4}$',
                                             max_length, min_length, *args, **kwargs)


class NOMunicipalitySelect(Select):
    """A Select widget that uses a list of Norwegian municipalities (fylker) as its choices."""

    def __init__(self, attrs=None):
        super(NOMunicipalitySelect, self).__init__(attrs, choices=MUNICIPALITY_CHOICES)


class NOSocialSecurityNumber(Field):
    """Algorithm is documented at http://no.wikipedia.org/wiki/Personnummer."""

    default_error_messages = {
        'invalid': _('Enter a valid Norwegian social security number.'),
    }

    def clean(self, value):
        super(NOSocialSecurityNumber, self).clean(value)
        if value in EMPTY_VALUES:
            return ''

        if not re.match(r'^\d{11}$', value):
            raise ValidationError(self.error_messages['invalid'])

        self.birthday = self._get_birthday(value)
        self.gender = self._get_gender(value)

        digits = map(int, list(value))
        weight_1 = [3, 7, 6, 1, 8, 9, 4, 5, 2, 1, 0]
        weight_2 = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2, 1]

        def multiply_reduce(aval, bval):
            return sum([(a * b) for (a, b) in zip(aval, bval)])

        if multiply_reduce(digits, weight_1) % 11 != 0:
            raise ValidationError(self.error_messages['invalid'])
        if multiply_reduce(digits, weight_2) % 11 != 0:
            raise ValidationError(self.error_messages['invalid'])

        return value

    def _get_gender(self, value):
        sexnum = int(value[8])
        if sexnum % 2 == 0:
            gender = 'F'
        else:
            gender = 'M'
        return gender

    def _get_birthday(self, value):
        birthday = None
        day = int(value[:2])
        month = int(value[2:4])
        year2 = int(value[4:6])
        inum = int(value[6:9])
        try:
            if 000 <= inum < 500:
                birthday = datetime.date(1900 + year2, month, day)
            if 500 <= inum < 750 and year2 > 54:
                birthday = datetime.date(1800 + year2, month, day)
            if 500 <= inum < 1000 and year2 < 40:
                birthday = datetime.date(2000 + year2, month, day)
            if 900 <= inum < 1000 and year2 > 39:
                birthday = datetime.date(1900 + year2, month, day)
        except ValueError:
            raise ValidationError(self.error_messages['invalid'])
        return birthday


class NOBankAccountNumber(EmptyValueCompatMixin, CharField):
    """
    A form field for Norwegian bank account numbers.

    Performs MOD11 with the custom weights for the Norwegian bank account numbers,
    including a check for a remainder of 0, in which event the checksum is also 0.

    Usually their string representation is along the lines of ZZZZ.YY.XXXXX, where the last X is the check digit.
    They're always a total of 11 digits long, with 10 out of these 11 being the actual account number itself.

    * Accepts, and strips, account numbers with extra spaces.
    * Accepts, and strips, account numbers provided in form of XXXX.YY.XXXXX.

    .. note:: No consideration is taking for banking clearing numbers as of yet, seeing as these are only used between
              banks themselves.

    .. versionadded:: 1.5
    """

    default_error_messages = {
        'invalid': _('Enter a valid Norwegian bank account number.'),
        'invalid_checksum': _('Invalid control digit. Enter a valid Norwegian bank account number.'),
        'invalid_length': _('Invalid length. Norwegian bank account numbers are 11 digits long.'),
    }

    def validate(self, value):
        super(NOBankAccountNumber, self).validate(value)

        if value in self.empty_values:
            # It's alright to be empty.
            return
        elif not value.isdigit():
            # You must only contain decimals.
            raise ValidationError(self.error_messages['invalid'])
        elif len(value) is not 11:
            # They only have one length: the number is 10!
            # That being said, you always store them with the check digit included, so 11.
            raise ValidationError(self.error_messages['invalid_length'])

        # The control/check digit is the last digit
        check_digit = int(value[-1])
        bank_number = value[:-1]

        # These are the weights by which we multiply to get our checksum digit
        weights = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
        result = sum(w * (int(x)) for w, x in zip(weights, bank_number))
        remainder = result % 11
        # The checksum is 0 in the event there's no remainder, seeing as we cannot have a checksum of 11
        # when 11 is one digit longer than we've got room for
        checksum = 0 if remainder is 0 else 11 - remainder

        if checksum != check_digit:
            raise ValidationError(self.error_messages['invalid_checksum'])

    def to_python(self, value):
        value = super(NOBankAccountNumber, self).to_python(value)
        if value in self.empty_values:
            return self.empty_value
        return value.replace('.', '').replace(' ', '')

    def prepare_value(self, value):
        value = self.to_python(value)
        if value in self.empty_values:
            return self.empty_value
        return '{}.{}.{}'.format(value[0:4], value[4:6], value[6:11])


class NOPhoneNumberField(RegexField, DeprecatedPhoneNumberFormFieldMixin):
    """
    Field with phonenumber validation.

    Requires a phone number with 8 digits and optional country code

    .. deprecated:: 1.4
        Use the django-phonenumber-field_ library instead.

    .. _django-phonenumber-field: https://github.com/stefanfoulis/django-phonenumber-field
    """

    default_error_messages = {
        'invalid': _('A phone number must be 8 digits and may have country code'),
    }

    def __init__(self, max_length=None, min_length=None, *args, **kwargs):
        super(NOPhoneNumberField, self).__init__(
            r'^(?:\+47)? ?(\d{3}\s?\d{2}\s?\d{3}|\d{2}\s?\d{2}\s?\d{2}\s?\d{2})$',
            max_length, min_length, *args, **kwargs)


class NOOrganisationNumberField(RegexField):
    """
    Validates the input of a Norwegian "organisasjonsnummer", which is a 9 digit number
    with the last digit being a checksum using the modulus 11 control digit algorithm.

    documented (in Norwegian) at:
        https://no.wikipedia.org/wiki/MOD11
    
    """

    default_error_messages = {'invalid': _("Please enter a valid Norwegian organisation number")}

    def __init__(self, max_length=18, min_length=9, *args, **kwargs):
        regex = re.compile(r'^(NO )?(\d{3}) ?(\d{3}) ?(\d{3})( MVA)?$', re.IGNORECASE)
        super(NOOrganisationNumberField, self).__init__(regex, max_length, min_length, *args, **kwargs)

    def to_python(self, value):
        match = self.regex.match(value)
        if match:
            groups = match.groups()
            prefix, suffix = groups[0] if groups[0] else '', groups[-1] if groups[-1] else ''
            return prefix + ''.join(match.groups()[1:4]) + suffix
        return value

    def clean(self, value):
        value = super(NOOrganisationNumberField, self).clean(value)
        if not value and not self.required:
            return value
        number = ''.join(self.regex.match(value).groups()[1:4])
        # Get a hold of the last digit as this is a checkdigit
        checkdigit = int(number[-1])
        #get the rest of the digits.
        digits = [int(x) for x in list(number[:8])]

        # weigh down each digit, then get the sum
        weights = [3, 2, 7, 6, 5, 4, 3, 2]
        result = sum(w * (int(x)) for w, x in zip(weights, digits))

        # mod11 the result
        remainder = result % 11

        #then make sure we dont have any 11s by making those instances 0
        checksum = 0 if remainder is 0 else 11 - remainder

        # if the checksum is wrong raise a validationerror
        if checksum != checkdigit:
            raise ValidationError(self.default_error_messages['invalid'], code='invalid')
        return value
