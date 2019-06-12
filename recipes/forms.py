from bootstrap_modal_forms.forms import BSModalForm

from .models import Order


class CreateOrderForm(BSModalForm):
    def __init__(self, *args, **kwargs):
        print(args, kwargs)
        super().__init__(*args, **kwargs)
        try:  # don't know why I'm hacking this and why initial does not work has supposed
            self.instance.mix = kwargs['initial']['mix']
        except KeyError:
            pass
        print(self.instance)

    def save(self, commit=True):
        print('save called')
        super().save(commit=commit)
        print('instance', self.instance)
        return self.instance

    class Meta:
        model = Order
        fields = ['mix', 'status']
