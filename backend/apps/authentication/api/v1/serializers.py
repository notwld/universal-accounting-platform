from rest_framework import serializers


class DeviceSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    platform = serializers.CharField(required=False, allow_blank=True, max_length=64)
    app_version = serializers.CharField(required=False, allow_blank=True, max_length=64)


class PreferencesSerializer(serializers.Serializer):
    timezone = serializers.CharField(required=False, allow_blank=True, max_length=64)
    locale = serializers.CharField(required=False, allow_blank=True, max_length=20)


class BootstrapSerializer(serializers.Serializer):
    device = DeviceSerializer(required=False)
    preferences = PreferencesSerializer(required=False)


class SwitchContextSerializer(serializers.Serializer):
    organization_id = serializers.CharField(max_length=36)
    location_id = serializers.CharField(required=False, allow_null=True, max_length=36)
