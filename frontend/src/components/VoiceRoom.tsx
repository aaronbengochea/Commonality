// LiveKit voice room component — Phase 4

interface Props {
  roomId: string;
  token: string;
}

export default function VoiceRoom({ roomId, token }: Props) {
  return (
    <div className="flex flex-col items-center gap-4">
      <p className="text-gray-500">Voice room: {roomId}</p>
      {/* TODO: LiveKit React components in Phase 4 */}
    </div>
  );
}
