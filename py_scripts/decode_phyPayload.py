''' 
	Functions to decode and decrypt the payload received by a gateway.

	Author: Dean Richert
	Date: 8/9/2017
'''

from lora.crypto import loramac_decrypt

def flipEndianess(str):
	N = len(str)
	flipped = ''
	for i in range(N,0,-2): 
		flipped += str[i-2:i]	
	return flipped
	
def decodePhyPayload(msg, AppSKey, DevAddr):
	# extract the physical payload from the message
	# and convert to hex
	char_seq = "phyPayload"
	idx = msg.payload.rfind(char_seq) + 13
	PHYPayload = msg.payload[idx:-2]
	PHYPayload = base64.decodestring(PHYPayload).encode('hex')
	
	# extract the MAC payload
	MACPayload = PHYPayload[2:-8]
	
	# decode the MAC payload
	DevAddr = flipEndianess(MACPayload[0:8])
	FOptsLen = int(MACPayload[9],16)
	FCnt = int(flipEndianess(MACPayload[10:14]),16)
	FRMPayload = MACPayload[14+2*FOptsLen+2:]
	
	# decrypt the FRM payload
	payload = loramac_decrypt(FRMPayload, FCnt, AppSKey, DevAddr)
	
	# convert to hex 
	payload_int = 0
	byte_num = len(payload)-1
	for byte in payload:
		payload_int += int(byte)*2**(8*byte_num)
		byte_num -= 1
	print format(payload_int, '#04x')