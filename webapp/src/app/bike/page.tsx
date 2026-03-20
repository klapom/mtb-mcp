'use client';

import { useState } from 'react';
import { useApi } from '@/hooks/useApi';
import { Card, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { LoadingState } from '@/components/ui/LoadingState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Modal } from '@/components/ui/Modal';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { ComponentWearBar } from '@/components/ComponentWearBar';
import { Bikes } from '@/lib/api';
import type { Bike, BikeComponent } from '@/lib/types';

export default function BikePage() {
  const { data: bikes, error, isLoading, mutate } = useApi<Bike[]>('/bikes');
  const [selectedBikeId, setSelectedBikeId] = useState<string | null>(null);
  const [rideModal, setRideModal] = useState<string | null>(null);
  const [serviceModal, setServiceModal] = useState<string | null>(null);

  // Ride form state
  const [rideDistance, setRideDistance] = useState('');
  const [rideDuration, setRideDuration] = useState('');

  // Service form state
  const [serviceComponentType, setServiceComponentType] = useState('chain');
  const [serviceAction, setServiceAction] = useState('');

  const {
    data: components,
    isLoading: componentsLoading,
    mutate: mutateComponents,
  } = useApi<BikeComponent[]>(selectedBikeId ? `/bikes/${selectedBikeId}/components` : null);

  const selectedBike = bikes?.find((b) => b.id === selectedBikeId);

  async function handleLogRide() {
    if (!rideModal || !rideDistance) return;
    await Bikes.logRide(rideModal, {
      distance_km: Number(rideDistance),
      duration_min: rideDuration ? Number(rideDuration) : undefined,
    });
    setRideModal(null);
    setRideDistance('');
    setRideDuration('');
    mutate();
    mutateComponents();
  }

  async function handleLogService() {
    if (!serviceModal || !serviceAction) return;
    await Bikes.logService(serviceModal, {
      component_type: serviceComponentType,
      action: serviceAction,
    });
    setServiceModal(null);
    setServiceAction('');
    setServiceComponentType('chain');
    mutate();
    mutateComponents();
  }

  if (isLoading) return <LoadingState text="Lade Bikes..." />;
  if (error) return <ErrorState message={error.message} onRetry={() => mutate()} />;

  return (
    <div className="p-4 pb-[calc(16px+var(--nav-height))]">
      <h1 className="text-lg font-bold mb-3">Bike Garage</h1>

      <div className="space-y-3">
        {bikes?.map((bike) => (
          <Card
            key={bike.id}
            className={selectedBikeId === bike.id ? 'border-accent-green' : ''}
          >
            <div
              className="cursor-pointer"
              onClick={() =>
                setSelectedBikeId(selectedBikeId === bike.id ? null : bike.id)
              }
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold">{bike.name}</span>
                <Badge variant="blue">{bike.type}</Badge>
              </div>

              <p className="text-sm text-text-secondary mb-2">
                {bike.total_km.toLocaleString()} km gesamt
              </p>

              {bike.worst_component && (
                <div className="mb-2">
                  <div className="flex items-center justify-between text-xs text-text-muted mb-1">
                    <span>{bike.worst_component}</span>
                    <span>{bike.worst_wear_pct}%</span>
                  </div>
                  <ProgressBar pct={bike.worst_wear_pct} />
                </div>
              )}
            </div>

            <div className="flex gap-2 mt-3">
              <button
                className="bg-accent-green text-white px-5 py-2.5 rounded-lg font-semibold text-sm"
                onClick={(e) => {
                  e.stopPropagation();
                  setRideModal(bike.id);
                }}
              >
                Fahrt loggen
              </button>
              <button
                className="bg-white/8 text-text-primary px-5 py-2.5 rounded-lg font-semibold text-sm"
                onClick={(e) => {
                  e.stopPropagation();
                  setServiceModal(bike.id);
                }}
              >
                Service
              </button>
            </div>
          </Card>
        ))}
      </div>

      {selectedBikeId && selectedBike && (
        <div className="mt-4">
          <Card>
            <CardHeader title={`Komponenten - ${selectedBike.name}`} />
            {componentsLoading ? (
              <LoadingState text="Lade Komponenten..." />
            ) : components && components.length > 0 ? (
              <div className="divide-y divide-border-subtle">
                {components.map((comp) => (
                  <ComponentWearBar key={comp.id} component={comp} />
                ))}
              </div>
            ) : (
              <p className="text-sm text-text-muted py-4 text-center">
                Keine Komponenten erfasst
              </p>
            )}
          </Card>
        </div>
      )}

      {/* Fahrt loggen Modal */}
      <Modal
        open={rideModal !== null}
        onClose={() => {
          setRideModal(null);
          setRideDistance('');
          setRideDuration('');
        }}
        title="Fahrt loggen"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">
              Distanz (km) *
            </label>
            <input
              type="number"
              value={rideDistance}
              onChange={(e) => setRideDistance(e.target.value)}
              placeholder="z.B. 42"
              className="w-full p-2.5 bg-bg-input border border-border-card rounded-lg text-sm text-text-primary focus:border-accent-green outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">
              Dauer (Minuten)
            </label>
            <input
              type="number"
              value={rideDuration}
              onChange={(e) => setRideDuration(e.target.value)}
              placeholder="optional"
              className="w-full p-2.5 bg-bg-input border border-border-card rounded-lg text-sm text-text-primary focus:border-accent-green outline-none"
            />
          </div>
          <button
            onClick={handleLogRide}
            disabled={!rideDistance}
            className="w-full bg-accent-green text-white px-5 py-2.5 rounded-lg font-semibold disabled:opacity-40"
          >
            Speichern
          </button>
        </div>
      </Modal>

      {/* Service Modal */}
      <Modal
        open={serviceModal !== null}
        onClose={() => {
          setServiceModal(null);
          setServiceAction('');
          setServiceComponentType('chain');
        }}
        title="Service loggen"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">
              Komponente
            </label>
            <select
              value={serviceComponentType}
              onChange={(e) => setServiceComponentType(e.target.value)}
              className="w-full p-2.5 bg-bg-input border border-border-card rounded-lg text-sm text-text-primary focus:border-accent-green outline-none"
            >
              <option value="chain">Kette</option>
              <option value="brake_pads">Bremsbel&auml;ge</option>
              <option value="tires">Reifen</option>
              <option value="cassette">Kassette</option>
              <option value="suspension">Federung</option>
              <option value="dropper">Dropper Post</option>
              <option value="brake_fluid">Bremse entl&uuml;ften</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">
              Aktion *
            </label>
            <input
              type="text"
              value={serviceAction}
              onChange={(e) => setServiceAction(e.target.value)}
              placeholder="replaced / cleaned / lubed"
              className="w-full p-2.5 bg-bg-input border border-border-card rounded-lg text-sm text-text-primary focus:border-accent-green outline-none"
            />
          </div>
          <button
            onClick={handleLogService}
            disabled={!serviceAction}
            className="w-full bg-accent-green text-white px-5 py-2.5 rounded-lg font-semibold disabled:opacity-40"
          >
            Speichern
          </button>
        </div>
      </Modal>
    </div>
  );
}
