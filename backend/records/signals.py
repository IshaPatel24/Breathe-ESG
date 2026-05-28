from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import ActivityRecord, AuditLog

def serialize_record_state(instance):
    """
    Serializes key fields of the ActivityRecord for AuditLog history.
    """
    return {
        'status': instance.status,
        'flag_reason': instance.flag_reason or "",
        'is_locked': instance.is_locked,
        'activity_value': str(instance.activity_value),
        'activity_unit': instance.activity_unit,
        'period_start': str(instance.period_start),
        'period_end': str(instance.period_end),
        'facility_code': instance.facility_code,
    }

@receiver(pre_save, sender=ActivityRecord)
def activity_record_pre_save(sender, instance, **kwargs):
    try:
        old_instance = ActivityRecord.objects.get(pk=instance.pk)
        instance._old_state = serialize_record_state(old_instance)
        instance._is_new = False
    except ActivityRecord.DoesNotExist:
        instance._old_state = {}
        instance._is_new = True

@receiver(post_save, sender=ActivityRecord)
def activity_record_post_save(sender, instance, created, **kwargs):
    # Determine the action type
    if created or getattr(instance, '_is_new', False):
        action = 'CREATED'
        before_state = {}
        after_state = serialize_record_state(instance)
    else:
        before_state = getattr(instance, '_old_state', {})
        after_state = serialize_record_state(instance)
        
        # Check if the status changed
        old_status = before_state.get('status')
        new_status = after_state.get('status')
        
        if old_status != new_status:
            if new_status == 'APPROVED':
                action = 'APPROVED'
            elif new_status == 'REJECTED':
                action = 'REJECTED'
            elif new_status == 'FLAGGED':
                action = 'FLAGGED'
            else:
                action = 'EDITED'
        else:
            # Check if any other serialized fields changed
            changed = False
            for k, v in after_state.items():
                if before_state.get(k) != v:
                    changed = True
                    break
            if changed:
                action = 'EDITED'
            else:
                return # No change worth logging

    # Retrieve current user if attached to instance (e.g. from DRF views)
    changed_by = getattr(instance, '_changed_by', None)

    AuditLog.objects.create(
        activity_record=instance,
        changed_by=changed_by,
        action=action,
        before_state=before_state,
        after_state=after_state
    )
