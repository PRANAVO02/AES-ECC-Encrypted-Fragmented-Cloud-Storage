package com.golance.backend.dto;

public class TransferRequestDto {

	private Long fromUserId;
	private Long toUserId;
	private int amount;   //amount refers to credits
	
	public Long getFromUserId() {
		return fromUserId;
	}
	public Long getToUserId() {
		return toUserId;
	}
	public int getAmount() {
		return amount;
	}
	public void setFromUserId(Long fromUserId) {
		this.fromUserId = fromUserId;
	}
	public void setToUserId(Long toUserId) {
		this.toUserId = toUserId;
	}
	public void setAmount(int amount) {
		this.amount = amount;
	}
	
}
