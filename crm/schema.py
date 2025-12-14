import re
import graphene
from graphene_django import DjangoObjectType
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from graphene_django.filter import DjangoFilterConnectionField
from .filters import CustomerFilter, ProductFilter, OrderFilter
from graphene import relay

from .models import Customer, Product, Order

class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        interfaces = (relay.Node,)
        fields = "__all__"


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        interfaces = (relay.Node,)
        fields = "__all__"


class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        interfaces = (relay.Node,)
        fields = "__all__"

class Query(graphene.ObjectType):
    all_customers = DjangoFilterConnectionField(
        CustomerType,
        filterset_class=CustomerFilter,
        order_by=graphene.String()
    )

    all_products = DjangoFilterConnectionField(
        ProductType,
        filterset_class=ProductFilter,
        order_by=graphene.String()
    )

    all_orders = DjangoFilterConnectionField(
        OrderType,
        filterset_class=OrderFilter,
        order_by=graphene.String()
    )

    def resolve_all_customers(self, info, **kwargs):
        qs = Customer.objects.all()
        order_by = kwargs.get("order_by")
        return qs.order_by(order_by) if order_by else qs

    def resolve_all_products(self, info, **kwargs):
        qs = Product.objects.all()
        order_by = kwargs.get("order_by")
        return qs.order_by(order_by) if order_by else qs

    def resolve_all_orders(self, info, **kwargs):
        qs = Order.objects.all()
        order_by = kwargs.get("order_by")
        return qs.order_by(order_by) if order_by else qs


# Mutations create customer
class CreateCustomer(graphene.Mutation):
    customer = graphene.Field(CustomerType)
    message = graphene.String()

    class Arguments:
        name = graphene.String(required=True)
        email = graphene.String(required=True)
        phone = graphene.String(required=False)

    def mutate(self, info, name, email, phone=None):
        if Customer.objects.filter(email=email).exists():
            raise Exception("Email already exists")

        if phone and not re.match(r"^(\+?\d{10,15}|(\d{3}-\d{3}-\d{4}))$", phone):
            raise Exception("Invalid phone format")

        customer = Customer.objects.create(
            name=name,
            email=email,
            phone=phone
        )

        return CreateCustomer(
            customer=customer,
            message="Customer created successfully"
        )
#Bulk customer creation
class BulkCreateCustomers(graphene.Mutation):
    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    class Arguments:
        customers = graphene.List(
            graphene.NonNull(
                graphene.InputObjectType(
                    "CustomerInput",
                    name=graphene.String(required=True),
                    email=graphene.String(required=True),
                    phone=graphene.String()
                )
            )
        )

    def mutate(self, info, customers):
        created = []
        errors = []

        for idx, data in enumerate(customers):
            try:
                if Customer.objects.filter(email=data.email).exists():
                    raise Exception("Email already exists")

                customer = Customer.objects.create(
                    name=data.name,
                    email=data.email,
                    phone=data.phone
                )
                created.append(customer)

            except Exception as e:
                errors.append(f"Row {idx + 1}: {str(e)}")

        return BulkCreateCustomers(customers=created, errors=errors)
# create product
class CreateProduct(graphene.Mutation):
    product = graphene.Field(ProductType)

    class Arguments:
        name = graphene.String(required=True)
        price = graphene.Decimal(required=True)
        stock = graphene.Int(required=False)

    def mutate(self, info, name, price, stock=0):
        if price <= 0:
            raise Exception("Price must be positive")

        if stock < 0:
            raise Exception("Stock cannot be negative")

        product = Product.objects.create(
            name=name,
            price=price,
            stock=stock
        )

        return CreateProduct(product=product)

#Create order

class CreateOrder(graphene.Mutation):
    order = graphene.Field(OrderType)

    class Arguments:
        customer_id = graphene.ID(required=True)
        product_ids = graphene.List(graphene.ID, required=True)
        order_date = graphene.DateTime(required=False)

    def mutate(self, info, customer_id, product_ids, order_date=None):
        if not product_ids:
            raise Exception("At least one product is required")

        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            raise Exception("Invalid customer ID")

        products = Product.objects.filter(id__in=product_ids)

        if products.count() != len(product_ids):
            raise Exception("One or more product IDs are invalid")

        total_amount = sum(product.price for product in products)

        order = Order.objects.create(
            customer=customer,
            total_amount=total_amount,
            order_date=order_date or now()
        )

        order.products.set(products)

        return CreateOrder(order=order)
# REgister mutations


class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()
