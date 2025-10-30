from rest_framework import serializers

from .models import Batch, Movement, MovementLine, Product


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = '__all__'
        read_only_fields = ('current_qty',)


class MovementLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovementLine
        fields = ('movement_line_id', 'sku', 'batch', 'quantity', 'note')


class MovementSerializer(serializers.ModelSerializer):
    lines = MovementLineSerializer(many=True)

    class Meta:
        model = Movement
        fields = (
            'movement_id',
            'ts',
            'type',
            'status',
            'from_warehouse',
            'to_warehouse',
            'channel',
            'external_ref',
            'created_by',
            'approved_by',
            'lines',
        )
        read_only_fields = ('status',)

    def create(self, validated_data):
        lines_data = validated_data.pop('lines', [])
        movement = Movement.objects.create(**validated_data)
        for line in lines_data:
            MovementLine.objects.create(movement=movement, **line)
        return movement

    def update(self, instance, validated_data):
        raise serializers.ValidationError('Updates not supported; create new movement instead.')
