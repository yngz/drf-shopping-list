from datetime import datetime, timedelta
from unittest import mock

import pytest
from django.urls import reverse
from django.utils.timezone import make_aware
from rest_framework import status
from shopping_list.models import ShoppingItem, ShoppingList, User


@pytest.mark.django_db
def test_valid_shopping_list_is_created(create_user, create_authenticated_client):
    url = reverse("all-shopping-lists")
    data = {
        "name": "Groceries",
    }
    client = create_authenticated_client(create_user())
    response = client.post(url, data, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert ShoppingList.objects.get().name == "Groceries"


@pytest.mark.django_db
def test_shopping_list_name_missing_returns_bad_request(
    create_user, create_authenticated_client
):
    url = reverse("all-shopping-lists")
    data = {"something_else": "blahblah"}

    client = create_authenticated_client(create_user())
    response = client.post(url, data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_client_retrieves_only_shopping_lists_they_are_member_of(
    create_user, create_authenticated_client, create_shopping_list
):
    user = create_user()
    shopping_list = ShoppingList.objects.create(name="Books")
    shopping_list.members.add(user)

    another_user = User.objects.create_user(
        "SomeoneElse", "someone@else.com", "something"
    )
    create_shopping_list(another_user)

    client = create_authenticated_client(user)
    url = reverse("all-shopping-lists")
    response = client.get(url)

    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["name"] == "Books"


@pytest.mark.django_db
def test_correct_order_shopping_lists(create_user, create_authenticated_client):
    user = create_user()
    client = create_authenticated_client(user)

    with mock.patch("django.utils.timezone.now") as mock_now:
        mock_now.return_value = make_aware(datetime.now()) - timedelta(days=1)
        ShoppingList.objects.create(name="Old").members.add(user)

        mock_now.return_value = make_aware(datetime.now()) - timedelta(days=100)
        ShoppingList.objects.create(name="Oldest").members.add(user)

    ShoppingList.objects.create(name="New").members.add(user)

    url = reverse("all-shopping-lists")
    response = client.get(url)

    assert response.data["results"][0]["name"] == "New"
    assert response.data["results"][1]["name"] == "Old"
    assert response.data["results"][2]["name"] == "Oldest"


@pytest.mark.django_db
def test_shopping_list_is_retrieved_by_id(
    create_user, create_authenticated_client, create_shopping_list
):
    user = create_user()
    client = create_authenticated_client(user)
    shopping_list = create_shopping_list(user)

    url = reverse("shopping-list-detail", args=[shopping_list.id])

    response = client.get(url, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["name"] == "Groceries"


@pytest.mark.django_db
def test_max_3_shopping_items_on_shopping_list(
    create_user, create_authenticated_client, create_shopping_list
):
    user = create_user()
    client = create_authenticated_client(user)

    shopping_list = create_shopping_list(user)

    ShoppingItem.objects.create(
        shopping_list=shopping_list, name="Eggs", purchased=False
    )
    ShoppingItem.objects.create(
        shopping_list=shopping_list, name="Chocolate", purchased=False
    )
    ShoppingItem.objects.create(
        shopping_list=shopping_list, name="Milk", purchased=False
    )
    ShoppingItem.objects.create(
        shopping_list=shopping_list, name="Mango", purchased=False
    )

    url = reverse("shopping-list-detail", args=[shopping_list.id])

    response = client.get(url, format="json")

    assert len(response.data["unpurchased_items"]) == 3


@pytest.mark.django_db
def test_all_shopping_items_on_shopping_list_unpurchased(
    create_user, create_authenticated_client, create_shopping_list
):
    user = create_user()
    client = create_authenticated_client(user)

    shopping_list = create_shopping_list(user)

    ShoppingItem.objects.create(
        shopping_list=shopping_list, name="Eggs", purchased=False
    )
    ShoppingItem.objects.create(
        shopping_list=shopping_list, name="Chocolate", purchased=True
    )
    ShoppingItem.objects.create(
        shopping_list=shopping_list, name="Milk", purchased=False
    )

    url = reverse("shopping-list-detail", args=[shopping_list.id])

    response = client.get(url, format="json")

    assert len(response.data["unpurchased_items"]) == 2


@pytest.mark.django_db
def test_admin_can_retrieve_shopping_list(
    create_user, create_shopping_list, admin_client
):

    user = create_user()
    shopping_list = create_shopping_list(user)

    url = reverse("shopping-list-detail", args=[shopping_list.id])

    response = admin_client.get(url, format="json")

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_shopping_list_includes_only_corresponding_items(
    create_user, create_authenticated_client
):
    user = create_user()
    client = create_authenticated_client(user)

    shopping_list = ShoppingList.objects.create(name="Groceries")
    shopping_list.members.add(user)
    another_shopping_list = ShoppingList.objects.create(name="Books")
    another_shopping_list.members.add(user)

    ShoppingItem.objects.create(
        shopping_list=shopping_list, name="Eggs", purchased=False
    )
    ShoppingItem.objects.create(
        shopping_list=another_shopping_list, name="The seven sisters", purchased=False
    )

    url = reverse("shopping-list-detail", args=[shopping_list.id])
    response = client.get(url)

    assert len(response.data["unpurchased_items"]) == 1
    assert response.data["unpurchased_items"][0]["name"] == "Eggs"


@pytest.mark.django_db
def test_shopping_list_name_is_changed(
    create_user, create_authenticated_client, create_shopping_list
):
    user = create_user()
    client = create_authenticated_client(user)
    shopping_list = create_shopping_list(user)

    url = reverse("shopping-list-detail", args=[shopping_list.id])

    data = {
        "name": "Food",
    }

    response = client.put(url, data=data, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["name"] == "Food"


@pytest.mark.django_db
def test_shopping_list_not_changed_because_name_missing(
    create_user, create_authenticated_client, create_shopping_list
):
    user = create_user()
    client = create_authenticated_client(user)
    shopping_list = create_shopping_list(user)

    url = reverse("shopping-list-detail", args=[shopping_list.id])

    data = {"something_else": "blahblah"}

    response = client.put(url, data=data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_update_shopping_list_restricted_if_not_member(
    create_user, create_authenticated_client, create_shopping_list
):
    user = create_user()
    shopping_list_creator = User.objects.create_user(
        "Creator", "creator@list.com", "something"
    )
    client = create_authenticated_client(user)
    shopping_list = create_shopping_list(shopping_list_creator)

    url = reverse("shopping-list-detail", args=[shopping_list.id])

    data = {
        "name": "Food",
    }

    response = client.put(url, data=data, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_shopping_list_name_is_changed_with_partial_update(
    create_user, create_authenticated_client, create_shopping_list
):
    user = create_user()
    client = create_authenticated_client(user)
    shopping_list = create_shopping_list(user)
    url = reverse("shopping-list-detail", args=[shopping_list.id])

    data = {
        "name": "Food",
    }

    response = client.patch(url, data=data, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["name"] == "Food"


@pytest.mark.django_db
def test_partial_update_with_missing_name_has_no_impact(
    create_user, create_authenticated_client, create_shopping_list
):
    user = create_user()
    client = create_authenticated_client(user)
    shopping_list = create_shopping_list(user)

    url = reverse("shopping-list-detail", args=[shopping_list.id])

    data = {"something_else": "blahblah"}

    response = client.patch(url, data=data, format="json")

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_partial_update_shopping_list_restricted_if_not_member(
    create_user, create_authenticated_client, create_shopping_list
):
    user = create_user()
    shopping_list_creator = User.objects.create_user(
        "Creator", "creator@list.com", "something"
    )
    client = create_authenticated_client(user)
    shopping_list = create_shopping_list(shopping_list_creator)

    url = reverse("shopping-list-detail", args=[shopping_list.id])

    data = {
        "name": "Food",
    }

    response = client.patch(url, data=data, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_shopping_list_is_deleted(
    create_user, create_authenticated_client, create_shopping_list
):
    user = create_user()
    client = create_authenticated_client(user)
    shopping_list = create_shopping_list(user)

    url = reverse("shopping-list-detail", args=[shopping_list.id])

    response = client.delete(url)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert len(ShoppingList.objects.all()) == 0


@pytest.mark.django_db
def test_delete_shopping_list_restricted_if_not_member(
    create_user, create_authenticated_client, create_shopping_list
):
    user = create_user()
    shopping_list_creator = User.objects.create_user(
        "Creator", "creator@list.com", "something"
    )
    client = create_authenticated_client(user)
    shopping_list = create_shopping_list(shopping_list_creator)

    url = reverse("shopping-list-detail", args=[shopping_list.id])

    response = client.delete(url, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_list_shopping_items_is_retrieved_by_shopping_list_member(
    create_user, create_authenticated_client, create_shopping_list
):
    user = create_user()
    shopping_list = create_shopping_list(user)
    shopping_item_1 = ShoppingItem.objects.create(
        name="Oranges", purchased=False, shopping_list=shopping_list
    )
    shopping_item_2 = ShoppingItem.objects.create(
        name="Milk", purchased=False, shopping_list=shopping_list
    )

    client = create_authenticated_client(user)
    url = reverse("list-add-shopping-item", kwargs={"pk": shopping_list.id})
    response = client.get(url)

    assert len(response.data["results"]) == 2
    assert response.data["results"][0]["name"] == shopping_item_1.name
    assert response.data["results"][1]["name"] == shopping_item_2.name


@pytest.mark.django_db
def test_not_member_can_not_retrieve_shopping_items(
    create_user, create_authenticated_client, create_shopping_item
):
    shopping_list_creator = User.objects.create_user(
        "SomeoneElse", "someone@else.com", "something"
    )
    shopping_item = create_shopping_item("Milk", shopping_list_creator)

    user = create_user()
    client = create_authenticated_client(user)
    url = reverse(
        "list-add-shopping-item", kwargs={"pk": shopping_item.shopping_list.id}
    )

    response = client.get(url)

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_list_shopping_items_only_the_ones_belonging_to_the_same_shopping_list(
    create_user, create_authenticated_client
):
    user = create_user()

    shopping_list = ShoppingList.objects.create(name="My shopping list")
    shopping_list.members.add(user)
    shopping_item_from_this_list = ShoppingItem.objects.create(
        name="Oranges", purchased=False, shopping_list=shopping_list
    )

    another_shopping_list = ShoppingList.objects.create(name="Another list")
    another_shopping_list.members.add(user)
    ShoppingItem.objects.create(
        name="Item from another list",
        purchased=False,
        shopping_list=another_shopping_list,
    )

    client = create_authenticated_client(user)
    url = reverse("list-add-shopping-item", kwargs={"pk": shopping_list.id})

    response = client.get(url)

    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["name"] == shopping_item_from_this_list.name


@pytest.mark.django_db
def test_valid_shopping_item_is_created(
    create_user, create_authenticated_client, create_shopping_list
):
    user = create_user()
    client = create_authenticated_client(user)
    shopping_list = create_shopping_list(user)

    url = reverse("list-add-shopping-item", args=[shopping_list.id])

    data = {"name": "Milk", "purchased": False}

    response = client.post(url, data, format="json")

    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_create_shopping_item_missing_data_returns_bad_request(
    create_user, create_authenticated_client, create_shopping_list
):
    user = create_user()
    client = create_authenticated_client(user)
    shopping_list = create_shopping_list(user)

    url = reverse("list-add-shopping-item", args=[shopping_list.id])

    data = {
        "name": "Milk",
    }

    response = client.post(url, data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_not_member_of_list_can_not_add_shopping_item(
    create_user, create_authenticated_client, create_shopping_list
):
    user = create_user()
    client = create_authenticated_client(user)
    shopping_list_creator = User.objects.create_user(
        "Creator", "creator@list.com", "something"
    )
    shopping_list = create_shopping_list(shopping_list_creator)

    url = reverse("list-add-shopping-item", args=[shopping_list.id])

    data = {"name": "Milk", "purchased": False}

    response = client.post(url, data, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_admin_can_add_shopping_items(create_user, create_shopping_list, admin_client):
    user = create_user()
    shopping_list = create_shopping_list(user)

    url = reverse("list-add-shopping-item", kwargs={"pk": shopping_list.id})

    data = {"name": "Milk", "purchased": False}

    response = admin_client.post(url, data, format="json")

    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_duplicate_item_on_list_bad_request(
    create_user, create_authenticated_client, create_shopping_list
):

    user = create_user()
    client = create_authenticated_client(user)
    shopping_list = create_shopping_list(user)
    ShoppingItem.objects.create(
        shopping_list=shopping_list, name="Milk", purchased=False
    )

    url = reverse("list-add-shopping-item", args=[shopping_list.id])

    data = {"name": "Milk", "purchased": False}

    response = client.post(url, data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert len(shopping_list.shopping_items.all()) == 1


@pytest.mark.django_db
def test_shopping_item_is_retrieved_by_id(
    create_user, create_authenticated_client, create_shopping_item
):
    user = create_user()
    client = create_authenticated_client(user)
    shopping_item = create_shopping_item(name="Chocolate", user=user)

    url = reverse(
        "shopping-item-detail",
        kwargs={"pk": shopping_item.shopping_list.id, "item_pk": shopping_item.id},
    )

    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["name"] == "Chocolate"


@pytest.mark.django_db
def test_shopping_item_detail_access_restricted_if_not_member_of_shopping_list(
    create_user, create_authenticated_client, create_shopping_item
):
    user = create_user()
    shopping_list_creator = User.objects.create_user(
        "Creator", "creator@list.com", "something"
    )
    client = create_authenticated_client(user)
    shopping_item = create_shopping_item(name="Chocolate", user=shopping_list_creator)

    url = reverse(
        "shopping-item-detail",
        kwargs={"pk": shopping_item.shopping_list.id, "item_pk": shopping_item.id},
    )

    response = client.get(url, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_admin_can_retrieve_single_shopping_item(
    create_user, create_shopping_item, admin_client
):
    user = create_user()
    shopping_item = create_shopping_item("Milk", user)

    url = reverse(
        "shopping-item-detail",
        kwargs={"pk": shopping_item.shopping_list.id, "item_pk": shopping_item.id},
    )

    response = admin_client.get(url)

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_change_shopping_item_purchased_status(
    create_user, create_authenticated_client, create_shopping_item
):
    user = create_user()
    client = create_authenticated_client(user)
    shopping_item = create_shopping_item(name="Chocolate", user=user)

    url = reverse(
        "shopping-item-detail",
        kwargs={"pk": shopping_item.shopping_list.id, "item_pk": shopping_item.id},
    )

    data = {"name": "Chocolate", "purchased": True}
    response = client.put(url, data, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert ShoppingItem.objects.get().purchased is True


@pytest.mark.django_db
def test_change_shopping_item_purchased_status_with_missing_data_returns_bad_request(
    create_user,
    create_authenticated_client,
    create_shopping_item,
):
    user = create_user()
    client = create_authenticated_client(user)
    shopping_item = create_shopping_item(name="Chocolate", user=user)

    url = reverse(
        "shopping-item-detail",
        kwargs={"pk": shopping_item.shopping_list.id, "item_pk": shopping_item.id},
    )

    data = {"purchased": True}
    response = client.put(url, data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_shopping_item_update_restricted_if_not_member_of_shopping_list(
    create_user, create_authenticated_client, create_shopping_item
):
    user = create_user()
    shopping_list_creator = User.objects.create_user(
        "Creator", "creator@list.com", "something"
    )
    client = create_authenticated_client(user)
    shopping_item = create_shopping_item(name="Chocolate", user=shopping_list_creator)

    url = reverse(
        "shopping-item-detail",
        kwargs={"pk": shopping_item.shopping_list.id, "item_pk": shopping_item.id},
    )

    data = {"name": "Chocolate", "purchased": True}

    response = client.put(url, data=data, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_change_shopping_item_purchased_status_with_partial_update(
    create_user,
    create_authenticated_client,
    create_shopping_item,
):
    user = create_user()
    client = create_authenticated_client(user)
    shopping_item = create_shopping_item(name="Chocolate", user=user)

    url = reverse(
        "shopping-item-detail",
        kwargs={"pk": shopping_item.shopping_list.id, "item_pk": shopping_item.id},
    )

    data = {"purchased": True}
    response = client.patch(url, data, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert ShoppingItem.objects.get().purchased is True


@pytest.mark.django_db
def test_shopping_item_partial_update_restricted_if_not_member_of_shopping_list(
    create_user, create_authenticated_client, create_shopping_item
):
    user = create_user()
    shopping_list_creator = User.objects.create_user(
        "Creator", "creator@list.com", "something"
    )
    client = create_authenticated_client(user)
    shopping_item = create_shopping_item(name="Chocolate", user=shopping_list_creator)

    url = reverse(
        "shopping-item-detail",
        kwargs={"pk": shopping_item.shopping_list.id, "item_pk": shopping_item.id},
    )

    data = {"purchased": True}

    response = client.patch(url, data=data, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_shopping_lists_order_changed_when_item_marked_purchased(
    create_user, create_authenticated_client
):
    user = create_user()
    client = create_authenticated_client(user)

    with mock.patch("django.utils.timezone.now") as mock_now:
        mock_now.return_value = make_aware(datetime.now()) - timedelta(days=20)
        older_list = ShoppingList.objects.create(name="Older")
        older_list.members.add(user)
        shopping_item_on_older_list = ShoppingItem.objects.create(
            name="Milk", purchased=False, shopping_list=older_list
        )

        mock_now.return_value = make_aware(datetime.now()) - timedelta(days=1)
        ShoppingList.objects.create(name="Recent").members.add(user)

    shopping_item_url = reverse(
        "shopping-item-detail",
        kwargs={"pk": older_list.id, "item_pk": shopping_item_on_older_list.id},
    )
    shopping_lists_url = reverse("all-shopping-lists")

    data = {"purchased": True}

    client.patch(shopping_item_url, data)

    response = client.get(shopping_lists_url)

    assert response.data["results"][0]["name"] == "Older"
    assert response.data["results"][1]["name"] == "Recent"


@pytest.mark.django_db
def test_shopping_item_is_deleted(
    create_user, create_authenticated_client, create_shopping_item
):
    user = create_user()
    client = create_authenticated_client(user)
    shopping_item = create_shopping_item(name="Chocolate", user=user)

    url = reverse(
        "shopping-item-detail",
        kwargs={"pk": shopping_item.shopping_list.id, "item_pk": shopping_item.id},
    )

    response = client.delete(url)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert len(ShoppingItem.objects.all()) == 0


@pytest.mark.django_db
def test_shopping_item_delete_restricted_if_not_member_of_shopping_list(
    create_user, create_authenticated_client, create_shopping_item
):
    user = create_user()
    shopping_list_creator = User.objects.create_user(
        "Creator", "creator@list.com", "something"
    )
    client = create_authenticated_client(user)
    shopping_item = create_shopping_item(name="Chocolate", user=shopping_list_creator)

    url = reverse(
        "shopping-item-detail",
        kwargs={"pk": shopping_item.shopping_list.id, "item_pk": shopping_item.id},
    )

    response = client.delete(url)

    assert response.status_code == status.HTTP_403_FORBIDDEN
