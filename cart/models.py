from django.db import models
from main.models import Product, ProductSize
from decimal import Decimal


class Cart(models.Model):
    session_key = models.CharField(max_length=40, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart {self.session_key}"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        # используем select_related чтобы уменьшить количество запросов
        qs = self.items.select_related('product', 'product_size').all()
        return sum((item.total_price for item in qs), Decimal('0.00'))

    def add_product(self, product, product_size, quantity=1):
        cart_item, created = CartItem.objects.get_or_create(
            cart=self,
            product=product,
            product_size=product_size,
            defaults={"quantity": quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        return cart_item

    def remove_item(self, item_id):
        try:
            item = self.items.get(id=item_id)
            item.delete()
            return True
        except CartItem.DoesNotExist:
            return False

    def update_item_quantity(self, item_id, quantity):
        try:
            item = self.items.get(id=item_id)
            if quantity > 0:
                item.quantity = quantity
                item.save()
            else:
                item.delete()
            return True
        except CartItem.DoesNotExist:
            return False

    def clear(self):
        self.items.all().delete()


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    product_size = models.ForeignKey(ProductSize, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cart", "product", "product_size")

    def __str__(self):
        # безопасное получение имени размера, если структура отличается — можно упростить
        size_name = getattr(self.product_size, 'size', None)
        size_display = getattr(size_name, 'name', str(self.product_size)) if size_name is not None else str(self.product_size)
        return f"{self.product.name} - {size_display} x {self.quantity}"

    @property
    def total_price(self):
        """
        Берёт цену из product_size если есть, иначе из product.
        Возвращает Decimal.
        """
        price = None
        if getattr(self, 'product_size', None) and getattr(self.product_size, 'price', None) is not None:
            price = self.product_size.price
        elif getattr(self, 'product', None) and getattr(self.product, 'price', None) is not None:
            price = self.product.price

        if price is None:
            return Decimal('0.00')

        # price ожидается Decimal (DecimalField), умножаем на Decimal(quantity)
        return price * Decimal(self.quantity)