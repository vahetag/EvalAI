from django.contrib.auth import get_user_model
from rest_auth.serializers import PasswordResetSerializer
from rest_framework.exceptions import ValidationError
from .models import JwtToken, Profile
from rest_framework import serializers

from rest_auth.registration.serializers import RegisterSerializer

class UserDetailsSerializer(serializers.ModelSerializer):
    """
    Make username as a read_only field.
    """

    class Meta:
        model = get_user_model()
        fields = (
            "pk",
            "email",
            "username",
            "first_name",
            "last_name",
            "password",
        )
        read_only_fields = ("email", "username")


class ProfileSerializer(UserDetailsSerializer):
    """
    Serializer to update the user profile.
    """

    affiliation = serializers.CharField(source="profile.affiliation", allow_blank=True)
    github_url = serializers.URLField(source="profile.github_url", allow_blank=True)
    google_scholar_url = serializers.URLField(source="profile.google_scholar_url", allow_blank=True)
    linkedin_url = serializers.URLField(source="profile.linkedin_url", allow_blank=True)

    confirmed_no_alphabet_affiliation = serializers.BooleanField(source="profile.confirmed_no_alphabet_affiliation", required=False)
    # receive_participated_challenge_updates = serializers.BooleanField(source="profile.receive_participated_challenge_updates", required=True)
    receive_participated_challenge_updates = serializers.BooleanField(source="profile.receive_participated_challenge_updates", required=False)
    recieve_newsletter = serializers.BooleanField(source="profile.recieve_newsletter", required=False)

    class Meta(UserDetailsSerializer.Meta):
        fields = (
            "pk",
            "email",
            "username",
            "first_name",
            "last_name",
            "affiliation",
            "github_url",
            "google_scholar_url",
            "linkedin_url",
            "confirmed_no_alphabet_affiliation",
            "receive_participated_challenge_updates",
            "recieve_newsletter",
        )

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", {})
        affiliation = profile_data.get("affiliation")
        github_url = profile_data.get("github_url")
        google_scholar_url = profile_data.get("google_scholar_url")
        linkedin_url = profile_data.get("linkedin_url")

        confirmed_no_alphabet_affiliation = profile_data.get("confirmed_no_alphabet_affiliation")
        receive_participated_challenge_updates = profile_data.get("receive_participated_challenge_updates")
        # receive_participated_challenge_updates = profile_data.get("receive_participated_challenge_updates", False)
        recieve_newsletter = profile_data.get("recieve_newsletter")

        instance = super(ProfileSerializer, self).update(instance, validated_data)

        profile = instance.profile
        if profile_data:
            profile.affiliation = affiliation
            profile.github_url = github_url
            profile.google_scholar_url = google_scholar_url
            profile.linkedin_url = linkedin_url
            profile.confirmed_no_alphabet_affiliation = confirmed_no_alphabet_affiliation
            profile.receive_participated_challenge_updates = receive_participated_challenge_updates
            profile.recieve_newsletter = recieve_newsletter
            profile.save()
        return instance


class UserProfileSerializer(UserDetailsSerializer):
    """
    Serializer to fetch the user profile.
    """

    class Meta:
        model = Profile
        fields = (
            "affiliation",
            "github_url",
            "google_scholar_url",
            "linkedin_url",
            "confirmed_no_alphabet_affiliation",
            "receive_participated_challenge_updates",
            "recieve_newsletter",
        )


class JwtTokenSerializer(serializers.ModelSerializer):
    """
    Serializer to update JWT token.
    """

    class Meta:
        model = JwtToken
        fields = (
            "user",
            "refresh_token",
            "access_token",
        )


class CustomPasswordResetSerializer(PasswordResetSerializer):
    """
    Serializer to check Account Active Status.
    """

    def get_email_options(self):
        try:
            user = get_user_model().objects.get(email=self.data["email"])
            if not user.is_active:
                raise ValidationError({"details": "Account is not active. Please contact the administrator."})
            else:
                return super().get_email_options()
        except get_user_model().DoesNotExist:
            raise ValidationError({"details": "User with the given email does not exist."})


class CustomRegisterSerializer(RegisterSerializer):
    affiliation = serializers.CharField(required=False, allow_blank=True)
    github_url = serializers.URLField(required=False, allow_blank=True)
    google_scholar_url = serializers.URLField(required=False, allow_blank=True)
    linkedin_url = serializers.URLField(required=False, allow_blank=True)
    confirmed_no_alphabet_affiliation = serializers.BooleanField(required=False)
    receive_participated_challenge_updates = serializers.BooleanField(required=False)
    recieve_newsletter = serializers.BooleanField(required=False)

    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        # Add your fields to the cleaned data
        data['affiliation'] = self.validated_data.get('affiliation', '')
        data['github_url'] = self.validated_data.get('github_url', '')
        data['google_scholar_url'] = self.validated_data.get('google_scholar_url', '')
        data['linkedin_url'] = self.validated_data.get('linkedin_url', '')
        data['confirmed_no_alphabet_affiliation'] = self.validated_data.get('confirmed_no_alphabet_affiliation', False)
        data['receive_participated_challenge_updates'] = self.validated_data.get('receive_participated_challenge_updates', False)
        data['recieve_newsletter'] = self.validated_data.get('recieve_newsletter', False)
        return data

    def save(self, request):
        user = super().save(request)
        user.save()

        # Now assign profile fields
        user.profile.affiliation = self.cleaned_data.get('affiliation')
        user.profile.github_url = self.cleaned_data.get('github_url')
        user.profile.google_scholar_url = self.cleaned_data.get('google_scholar_url')
        user.profile.linkedin_url = self.cleaned_data.get('linkedin_url')
        user.profile.confirmed_no_alphabet_affiliation = self.cleaned_data.get('confirmed_no_alphabet_affiliation')
        user.profile.receive_participated_challenge_updates = self.cleaned_data.get('receive_participated_challenge_updates')
        user.profile.recieve_newsletter = self.cleaned_data.get('recieve_newsletter')

        user.profile.save()
        return user