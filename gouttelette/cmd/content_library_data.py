#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2023, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

content_library_static_ds = {
    "{@term field}": "field",
    "{@name Vcenter}": "vCenter",
    "{@link LibraryModel}": "Library",
    "{@term unset}": "not set",
    "{@link StorageBacking}": "storage backing",
    "{@name LibraryModel}": "Library",
    "{@link PublishInfo}": "C(publish_info)",
    "{@link PublishInfo#published}": "C(publish_info.published)",
    "{@link SubscriptionInfo}": "C(subscription_info)",
    "{@link SubscriptionInfo#automaticSyncEnabled}": "C(subscription_info.automaticSyncEnabled)",
    "{@link SubscriptionInfo#subscriptionUrl}": "C(subscription_info.subscriptionurl)",
    "{@link LibraryModel#name}": "C(Library name)",
    "{@link StorageBacking#storageUri}": "C(storage_backings.storage_uri)",
    "{@link PublishInfo#persistJsonEnabled}": "C(publish_info.persist_json_enabled)",
    "{@link PublishInfo#publishUrl}": "C(publish_info.publish_url)",
    "{@link ConfigurationModel#automaticSyncEnabled}": "C(configuration_model.automatic_sync_enabled)",
    "{@link SubscribedLibrary#sync}": "M(vmware.vmware_rest.content_subscribedlibrary) with C(state=sync)",
    "{@link SubscribedItem#sync}": "M(vmware.vmware_rest.content_library_item) with C(state=sync)",
    "{@link SubscribedItem#evict}": "M(vmware.vmware_rest.content_library_item) with C(state=sync)",
    "{@link ItemModel}": "item",
    "{@link Processes#create}": "process",
}
